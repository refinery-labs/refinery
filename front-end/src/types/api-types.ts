
export interface BaseApiResponse {
  success: boolean
}

export interface ProjectSearchResultResponse extends BaseApiResponse {
  results: ProjectSearchResult[]
}

export interface ProjectSearchResult {
  timestamp: number,
  versions: number[],
  id: string,
  name: string
}
