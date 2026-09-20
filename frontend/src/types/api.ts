/** Shared API / transport types. */

/** Standard error envelope exposed by the backend adapter. */
export interface ApiErrorPayload {
  error: string;
  error_type?: string;
  message?: string;
  context?: Record<string, string>;
  status?: number;
}

/** Wrapper thrown by the API client for typed error handling. */
export class ApiError extends Error {
  readonly kind: string;
  readonly status: number | null;
  readonly context: Record<string, string> | null;

  constructor(message: string, kind = "ApiError", status: number | null = null, context: Record<string, string> | null = null) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.context = context;
  }
}

/** Generic paginated response. */
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

/** List query parameters shared by runs/datasets/artifacts endpoints. */
export interface ListQuery {
  page?: number;
  pageSize?: number;
  sort?: string;
  order?: "asc" | "desc";
  status?: string;
  taskType?: string;
  search?: string;
  dataset?: string;
  dateFrom?: string;
  dateTo?: string;
}