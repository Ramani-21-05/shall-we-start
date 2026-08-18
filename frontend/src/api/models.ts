// src/api/models.ts
import api from './client'

export const fetchChampionModel = async (drug: string) => {
  const res = await api.get(`/models/${drug}/champion`)
  return res.data.data
}

