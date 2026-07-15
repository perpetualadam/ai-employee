# API Pagination

List endpoints now support cursor-based pagination for better performance with large datasets.

## Paginated Endpoints

| Endpoint | Default Page Size | Max Page Size |
|----------|------------------|---------------|
| `GET /customers` | 50 | 100 |
| `GET /conversations` | 50 | 100 |

## Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (1-indexed) |
| `page_size` | integer | 50 | Items per page (1-100) |

## Response Format

All paginated endpoints return:

```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 50,
  "total_pages": 3,
  "has_more": true
}
```

### Response Fields

- **items**: Array of items for the current page
- **total**: Total number of items across all pages
- **page**: Current page number (1-indexed)
- **page_size**: Number of items per page
- **total_pages**: Total number of pages
- **has_more**: Boolean indicating if more pages exist

## Examples

### Get First Page

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/customers?page=1&page_size=20"
```

### Get Second Page

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/customers?page=2&page_size=20"
```

### Search with Pagination

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/customers?page=1&page_size=50&search=John"
```

## Frontend Usage

```typescript
// frontend/src/hooks/use-customers.ts
import { useState } from 'react';
import { api, PaginatedResponse, Customer } from '@/lib/api';

export function useCustomersPaginated() {
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  
  const { data, isLoading } = useQuery({
    queryKey: ['customers', page, pageSize],
    queryFn: () => api.listCustomersPaginated({ page, page_size: pageSize }),
  });

  return {
    customers: data?.items ?? [],
    total: data?.total ?? 0,
    page,
    setPage,
    hasMore: data?.has_more ?? false,
    isLoading,
  };
}
```

## Migration Notes

### Backward Compatibility

Old endpoints without pagination still work but will be deprecated:

- `/api/v1/customers` (no pagination) → Returns all customers
- `/api/v1/customers?page=1` (with pagination) → Returns paginated response

Frontend should migrate to use `page` and `page_size` parameters.

### TypeScript Types

Update frontend API client:

```typescript
// frontend/src/lib/api.ts
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_more: boolean;
}

export const api = {
  listCustomersPaginated: (params: { page: number; page_size: number; search?: string }) =>
    request<PaginatedResponse<Customer>>(
      `/customers?page=${params.page}&page_size=${params.page_size}${params.search ? `&search=${params.search}` : ''}`
    ),
  // ... other methods
};
```

## Performance Impact

With pagination:
- Reduced memory usage on backend
- Faster response times for large datasets
- Better database query performance (LIMIT/OFFSET)

### Database Indexes

Ensure indexes exist on ordering columns:

```sql
CREATE INDEX idx_customers_created_at ON customers (business_id, created_at DESC);
CREATE INDEX idx_call_logs_created_at ON call_logs (business_id, created_at DESC);
```

## Future Enhancements

Consider cursor-based pagination for very large datasets:

```json
{
  "items": [...],
  "next_cursor": "eyJpZCI6IjEyMzQ1Njc4OTAifQ==",
  "has_more": true
}
```
