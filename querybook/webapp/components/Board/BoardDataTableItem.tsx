import { ContentState } from 'draft-js';
import * as React from 'react';
import { useDispatch } from 'react-redux';

import { useShallowSelector } from 'hooks/redux/useShallowSelector';
import { fetchDataTableIfNeeded } from 'redux/dataSources/action';
import { Dispatch, IStoreState } from 'redux/store/types';
import { RichTextEditor } from 'ui/RichTextEditor/RichTextEditor';

import { BoardItem } from './BoardItem';

interface IProps {
    tableId: number;
    isCollapsed: boolean;
    isEditMode: boolean;
}

export const BoardDataTableItem: React.FunctionComponent<IProps> = ({
    tableId,
    isCollapsed,
    isEditMode,
}) => {
    const { table, schema } = useShallowSelector((state: IStoreState) => {
        const tableFromState = state.dataSources.dataTablesById[tableId];
        const schemaFromState = tableFromState
            ? state.dataSources.dataSchemasById[tableFromState.schema]
            : null;

        return {
            table: tableFromState,
            schema: schemaFromState,
        };
    });

    const dispatch: Dispatch = useDispatch();

    React.useEffect(() => {
        dispatch(fetchDataTableIfNeeded(tableId));
    }, [tableId]);

    // TODO - meowcodes: make this editable when applicable
    const notesDOM = (table.description as ContentState).getPlainText()
        .length ? (
        <RichTextEditor
            value={table.description as ContentState}
            readOnly={true}
            className="mt8"
        />
    ) : null;

    return (
        <BoardItem
            itemId={table.id}
            itemType="table"
            title={`${schema?.name}.${table.name}`}
            titleUrl={`/table/${table.id}/`}
            notesDOM={notesDOM}
            defaultCollapsed={isCollapsed}
            isEditMode={isEditMode}
        />
    );
};
