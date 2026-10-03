import axios from 'axios'

const API = axios.create({
  baseURL: 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

export const login = (user_id, password) =>
  API.post('/login', { user_id, password })

export const chat = (payload) =>
  API.post('/chat', payload)

export const getAudit = (request_id) =>
  API.get(`/audit/${request_id}`)