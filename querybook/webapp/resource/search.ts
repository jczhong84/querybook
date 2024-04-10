import { IDataSchema } from 'const/metastore';
import type {
    IBoardPreview,
    IDataDocPreview,
    IQueryPreview,
    ISearchBoardParams,
    ISearchDataDocParams,
    ISearchQueryParams,
    ISearchTableParams,
    ISearchUserParams,
    ITablePreview,
    IUserSearchResultRow,
} from 'const/search';
import ds from 'lib/datasource';
import type { ITableSearchResult } from 'redux/dataTableSearch/types';

export const SearchTableResource = {
    searchConcise: (params: ISearchTableParams) =>
        ds.fetch<{
            results: ITableSearchResult[];
            count: number;
        }>('/search/tables/', { ...params, concise: true }),

    search: (params: ISearchTableParams) =>
        ds.fetch<{
            results: ITablePreview[];
            count: number;
        }>('/search/tables/', { ...params, concise: false }),

    vectorSearch: (params: ISearchTableParams) =>
        ds.fetch<{
            results: ITablePreview[];
            count: number;
        }>('/search/tables/vector/', { ...params }),

    suggest: (metastoreId: number, keyword: string) =>
        ds.fetch<string[]>(`/suggest/${metastoreId}/tables/`, {
            keyword,
        }),
};

export const SearchSchemaResource = {
    getMore: ({
        offset = 0,
        limit = 30,
        sort_key = 'name',
        sort_order = 'asc',
        ...params
    }: {
        metastore_id: number;
        offset?: number;
        limit?: number;
        sort_key?: 'name' | 'table_count';
        sort_order?: 'desc' | 'asc';
        name?: string;
    }) =>
        ds.fetch<{
            results: IDataSchema[];
            done: boolean;
        }>('/schemas/', { offset, limit, sort_key, sort_order, ...params }),
};

export const SearchQueryResource = {
    search: (params: ISearchQueryParams) =>
        ds.fetch<{
            results: IQueryPreview[];
            count: number;
        }>('/search/queries/', params as unknown as Record<string, unknown>),
};

export const SearchDataDocResource = {
    search: (params: ISearchDataDocParams) =>
        ds.fetch<{
            results: IDataDocPreview[];
            count: number;
        }>('/search/datadoc/', params as unknown as Record<string, unknown>),
};

export const SearchUserResource = {
    search: (params: ISearchUserParams) =>
        ds.fetch<IUserSearchResultRow[]>(
            '/search/user/',
            params as unknown as Record<string, unknown>
        ),
};

export const SearchBoardResource = {
    search: (params: ISearchBoardParams) =>
        ds.fetch<{
            results: IBoardPreview[];
            count: number;
        }>(`/search/board/`, params as unknown as Record<string, unknown>),
};
