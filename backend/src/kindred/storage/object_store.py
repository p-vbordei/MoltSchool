from typing import Protocol


class ObjectNotFoundError(Exception):
    pass


class ObjectStore(Protocol):
    async def put(self, content_id: str, data: bytes) -> None: ...
    async def get(self, content_id: str) -> bytes: ...
    async def exists(self, content_id: str) -> bool: ...


class InMemoryObjectStore:
    def __init__(self) -> None:
        self._data: dict[str, bytes] = {}

    async def put(self, content_id: str, data: bytes) -> None:
        self._data[content_id] = data

    async def get(self, content_id: str) -> bytes:
        if content_id not in self._data:
            raise ObjectNotFoundError(content_id)
        return self._data[content_id]

    async def exists(self, content_id: str) -> bool:
        return content_id in self._data


class PostgresObjectStore:
    """Stores artifact bodies as BYTEA rows in the same Postgres DB.

    Suitable when artifact bodies are small (markdown, config snippets) and
    scale is modest — avoids running a separate object-store service. Adapter
    is API-compatible with MinioObjectStore, so swapping later for MinIO/R2/S3
    is a single env-var change; data migration is a row-by-row copy if needed.

    Content-addressed: `content_id` is PK, so duplicate puts are idempotent by
    primary-key constraint (IntegrityError caught and ignored).
    """

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def put(self, content_id: str, data: bytes) -> None:
        from sqlalchemy import text
        from sqlalchemy.exc import IntegrityError

        async with self._session_factory() as s:
            try:
                await s.execute(
                    text(
                        "INSERT INTO artifact_bodies (content_id, data) "
                        "VALUES (:cid, :data)"
                    ),
                    {"cid": content_id, "data": data},
                )
                await s.commit()
            except IntegrityError:
                # Same cid already stored; content-addressed = same bytes. Idempotent.
                await s.rollback()

    async def get(self, content_id: str) -> bytes:
        from sqlalchemy import text

        async with self._session_factory() as s:
            result = await s.execute(
                text("SELECT data FROM artifact_bodies WHERE content_id = :cid"),
                {"cid": content_id},
            )
            row = result.one_or_none()
            if row is None:
                raise ObjectNotFoundError(content_id)
            return bytes(row[0])

    async def exists(self, content_id: str) -> bool:
        from sqlalchemy import text

        async with self._session_factory() as s:
            result = await s.execute(
                text("SELECT 1 FROM artifact_bodies WHERE content_id = :cid"),
                {"cid": content_id},
            )
            return result.one_or_none() is not None


class MinioObjectStore:
    def __init__(self, endpoint: str, access: str, secret: str, bucket: str) -> None:
        from minio import Minio

        self._client = Minio(
            endpoint.removeprefix("http://").removeprefix("https://"),
            access_key=access,
            secret_key=secret,
            secure=endpoint.startswith("https"),
        )
        self._bucket = bucket
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)

    async def put(self, content_id: str, data: bytes) -> None:
        import io

        self._client.put_object(self._bucket, content_id, io.BytesIO(data), len(data))

    async def get(self, content_id: str) -> bytes:
        from minio.error import S3Error

        try:
            resp = self._client.get_object(self._bucket, content_id)
            try:
                return resp.read()
            finally:
                resp.close()
                resp.release_conn()
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise ObjectNotFoundError(content_id) from e
            raise

    async def exists(self, content_id: str) -> bool:
        from minio.error import S3Error

        try:
            self._client.stat_object(self._bucket, content_id)
            return True
        except S3Error:
            return False
