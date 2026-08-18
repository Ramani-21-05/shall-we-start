// src/utils/errorUtils.ts

/**
 * Safely extracts a human-readable string error message from any API error object,
 * Axios error, Fetch response, or thrown value.
 * Properly formats FastAPI / Pydantic HTTP 422 Unprocessable Content error lists/objects
 * to prevent React "Objects are not valid as a React child" rendering errors.
 */
export function getErrorMessage(err: unknown, fallback = 'An unexpected error occurred.'): string {
  if (!err) return fallback

  if (typeof err === 'string') return err

  if (typeof err === 'object') {
    const errorObj = err as Record<string, any>

    // Extract detail from Axios response or API error object
    const detail = errorObj.response?.data?.detail ?? errorObj.detail ?? errorObj.data?.detail

    if (detail !== undefined && detail !== null) {
      if (typeof detail === 'string') {
        return detail
      }

      if (Array.isArray(detail)) {
        // FastAPI 422 validation errors array: [{ loc: [...], msg: "...", type: "..." }]
        const messages = detail.map((item: any) => {
          if (typeof item === 'string') return item
          if (typeof item === 'object' && item !== null) {
            const fieldPath = Array.isArray(item.loc)
              ? item.loc.filter((l: any) => l !== 'body' && l !== 'query' && l !== 'path').join('.')
              : ''
            const msg = item.msg || JSON.stringify(item)
            return fieldPath ? `${fieldPath}: ${msg}` : msg
          }
          return String(item)
        })
        return messages.filter(Boolean).join('; ') || fallback
      }

      if (typeof detail === 'object') {
        if (typeof detail.msg === 'string') return detail.msg
        try {
          return JSON.stringify(detail)
        } catch {
          return fallback
        }
      }
    }

    if (typeof errorObj.message === 'string') {
      return errorObj.message
    }
  }

  return fallback
}
