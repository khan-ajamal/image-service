# Image Service

A Flask-based REST API for managing image uploads and metadata, backed by AWS S3 (object storage) and DynamoDB (metadata).

---

## DynamoDB Table Design

**Table:** `images`

| Key Type           | Attribute  | Description             |
| ------------------ | ---------- | ----------------------- |
| Partition Key (PK) | `user_id`  | Owner of the image      |
| Sort Key (SK)      | `image_id` | Unique image identifier |

### Global Secondary Indexes (GSIs)

| Index Name       | Partition Key | Sort Key   | Used For                          |
| ---------------- | ------------- | ---------- | --------------------------------- |
| `image_id-index` | `image_id`    | —          | Get / Delete a single image by ID |
| `category-index` | `category`    | `image_id` | List images filtered by category  |

### Query → Index Mapping

| Query                          | Access Pattern                          |
| ------------------------------ | --------------------------------------- |
| Get image by ID                | GSI `image_id-index`                    |
| List by `user_id`              | Base table query (PK = `user_id`)       |
| List by `category`             | GSI `category-index`                    |
| List by `user_id` + `category` | Base table query + filter on `category` |

> In production all API calls are authenticated, so `user_id` is always available — a full table scan is never needed.

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/khan-ajamal/image-service.git
cd image-service
```

### 2. Install dependencies

```bash
uv sync --all-groups
```

### 3. Start LocalStack

```bash
make up
```

This starts LocalStack via Docker Compose and automatically provisions the S3 bucket and DynamoDB table.

### 4. Run the application

```bash
make dev
```

Starts LocalStack (if not already running) and the Flask dev server at **http://localhost:8000**.

### 5. Run tests

```bash
make test
```

---

## API Documentation

The full API specification is available in OpenAPI 3.0 format: [`openapi.yaml`](openapi.yaml).

All endpoints are prefixed with `/images`.

| Method | Path                | Description                         | Success |
| ------ | ------------------- | ----------------------------------- | ------- |
| POST   | `/images/upload`    | Get a presigned S3 upload URL       | 200     |
| POST   | `/images/`          | Create an image metadata record     | 201     |
| GET    | `/images/:image_id` | Get image metadata by ID            | 200     |
| GET    | `/images/`          | List images (paginated, filterable) | 200     |
| DELETE | `/images/:image_id` | Delete image and its S3 object      | 204     |

---

## Bruno (API Client)

Install [Bruno](https://www.usebruno.com/) and load the `api-docs/` folder to browse and test all API requests and responses interactively.

> **Note:** Uploading a file to the presigned URL does not work reliably inside Bruno. Use the following `curl` command instead:
>
> ```bash
> curl --request PUT \
>   --url <presigned_url> \
>   --header 'content-type: application/octet-stream' \
>   --upload-file <path-to-file>
> ```
