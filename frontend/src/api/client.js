import axios from 'axios'

// Backend-API (über nginx auf http://backend:8000)
const client = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// Kratos (über nginx auf http://na-kratos:4433) – eigenes Prefix /kratos
export const kratos = axios.create({
  baseURL: '/kratos',
  timeout: 15000,
})

export default client
