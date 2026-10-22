import client from '@/api/client'

// Installer-API (eigene Kunden/Anlagen, auth via Kratos-Session + Oathkeeper)
const installer = {
  async listCustomers() {
    const { data } = await client.get('/installer/customers')
    return data
  },
  async searchCustomers(q) {
    const { data } = await client.get('/installer/customers/search', { params: { q } })
    return data
  },
  async getCustomer(id) {
    const { data } = await client.get(`/installer/customers/${id}`)
    return data
  },
  async createCustomer(payload) {
    const { data } = await client.post('/installer/customers', payload)
    return data
  },
  async updateCustomer(id, payload) {
    const { data } = await client.put(`/installer/customers/${id}`, payload)
    return data
  },
  async deleteCustomer(id) {
    await client.delete(`/installer/customers/${id}`)
  },
}

export default installer
