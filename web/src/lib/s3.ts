import { CreateBucketCommand, GetObjectCommand, HeadBucketCommand, HeadObjectCommand, PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { promises as fs } from "node:fs";
import path from "node:path";

function blobRoot() {
  return path.join(process.cwd(), "..", "data", "blobs");
}

function usesS3() {
  return Boolean(process.env.S3_ENDPOINT);
}

function bucket() {
  return process.env.S3_BUCKET || "ken";
}

function client() {
  return new S3Client({
    region: process.env.S3_REGION || "us-east-1",
    endpoint: process.env.S3_ENDPOINT,
    forcePathStyle: true,
    credentials: {
      accessKeyId: process.env.S3_ACCESS_KEY || "minio",
      secretAccessKey: process.env.S3_SECRET_KEY || "minio-password",
    },
  });
}

export function copyKey(copyId: string, name: string) {
  return `copies/${copyId}/${name}`;
}

export async function ensureBucket() {
  if (!usesS3()) {
    await fs.mkdir(blobRoot(), { recursive: true });
    return;
  }
  const s3 = client();
  const name = bucket();
  try {
    await s3.send(new HeadBucketCommand({ Bucket: name }));
  } catch {
    await s3.send(new CreateBucketCommand({ Bucket: name }));
  }
}

export async function putBytes(key: string, body: Buffer, contentType: string) {
  await ensureBucket();
  if (usesS3()) {
    await client().send(
      new PutObjectCommand({ Bucket: bucket(), Key: key, Body: body, ContentType: contentType }),
    );
    return;
  }
  const dest = path.join(blobRoot(), key);
  await fs.mkdir(path.dirname(dest), { recursive: true });
  await fs.writeFile(dest, body);
}

export async function getBytes(key: string): Promise<Buffer> {
  if (usesS3()) {
    const res = await client().send(new GetObjectCommand({ Bucket: bucket(), Key: key }));
    const bytes = await res.Body?.transformToByteArray();
    if (!bytes) throw new Error(`Empty object ${key}`);
    return Buffer.from(bytes);
  }
  return fs.readFile(path.join(blobRoot(), key));
}

export async function objectExists(key: string): Promise<boolean> {
  if (usesS3()) {
    try {
      await client().send(new HeadObjectCommand({ Bucket: bucket(), Key: key }));
      return true;
    } catch {
      return false;
    }
  }
  try {
    await fs.access(path.join(blobRoot(), key));
    return true;
  } catch {
    return false;
  }
}
