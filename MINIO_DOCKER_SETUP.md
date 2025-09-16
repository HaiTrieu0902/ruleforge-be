
# MinIO Docker Setup Guide

## 1. Run MinIO server with Docker
```bash
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9090:9090 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin123 \
  quay.io/minio/minio server /data --console-address ":9090"
```
Or on Windows PowerShell:
```powershell
docker run -d --name minio -p 9000:9000 -p 9090:9090 -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin123 quay.io/minio/minio server /data --console-address ":9090"  
```
- `9000`: S3 API port (use this for upload/download)
- `9090`: Web console port (for management)
- `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`: admin credentials
- `/data`: directory inside container for object storage

- Web console: http://localhost:9090 (login with minioadmin / minioadmin123)
- API S3: http://localhost:9000


## 3. Create a bucket

- Go to the web console → "Buckets" → "Create Bucket" → enter a name (e.g., `mybucket`)


## 4. Upload thử file
- Dùng web console hoặc MinIO Client CLI:
```bash
docker run -it --rm \
  --name mc \
  --link minio \
  -e MC_HOST_minio=http://minioadmin:minioadmin123@minio:9000 \
  quay.io/minio/mc ls minio
```


n