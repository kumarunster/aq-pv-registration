import client from './client'

/**
 * Dokumentations-Bilder (MinIO via /api/docs).
 */
export async function uploadImage(customerId, plantIndex, file) {
  const form = new FormData()
  form.append('file', file)
  const r = await client.post(
    `/docs/customers/${customerId}/plants/${plantIndex}/upload`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return r.data
}

export function imageUrl(customerId, plantIndex, blobKey) {
  return `/api/docs/customers/${customerId}/plants/${plantIndex}/${encodeURIComponent(blobKey)}`
}

export async function deleteImage(customerId, plantIndex, blobKey) {
  await client.delete(`/docs/customers/${customerId}/plants/${plantIndex}/${encodeURIComponent(blobKey)}`)
}
