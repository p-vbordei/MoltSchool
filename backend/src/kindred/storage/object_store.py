from typing import Protocol


class ObjectNotFound(Exception):
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
            raise ObjectNotFound(content_id)
        return self._data[content_id]

    async def exists(self, content_id: str) -> bool:
        return content_id in self._data


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
                raise ObjectNotFound(content_id) from e
            raise

    async def exists(self, content_id: str) -> bool:
        from minio.error import S3Error

        try:
            self._client.stat_object(self._bucket, content_id)
            return True
        except S3Error:
            return False
