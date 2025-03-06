import React from 'react';
import { connect } from 'react-redux';
import { AsyncButton } from 'ui/AsyncButton/AsyncButton';
import { Icon } from 'ui/Icon/Icon';
import { BoundQueryEditor } from 'components/QueryEditor/BoundQueryEditor';
import { runPythonCode } from 'lib/web-worker/python-worker';
import { createQueryExecution } from 'redux/queryExecutions/action';
import { IStoreState } from 'redux/store/types';
import './DataDocPythonCell.scss';

interface IDataDocPythonCellProps {
    cellId: number;
    docId: number;
    context: string;
    isEditable: boolean;
    onChange: (fields: { context: string }) => void;
    createQueryExecution: (
        query: string,
        engineId: number,
        cellId: number,
        metadata: Record<string, any>
    ) => Promise<number>;
}

class DataDocPythonCellComponent extends React.PureComponent<IDataDocPythonCellProps> {
    handleCodeChange = (newCode: string) => {
        this.props.onChange({ context: newCode });
    };

    runPythonCode = async () => {
        const { context, cellId, docId, createQueryExecution } = this.props;

        try {
            const result = await runPythonCode(context);
            await createQueryExecution(context, 0, cellId, { docId, result });
            // Handle the result (e.g., display output)
        } catch (error) {
            console.error('Failed to run Python code:', error);
            // Handle the error (e.g., display error message)
        }
    };

    render() {
        const { isEditable, context } = this.props;

        return (
            <div className="DataDocPythonCell">
                <div className="python-cell-header">
                    <h3>Python Cell</h3>
                    <AsyncButton
                        onClick={this.runPythonCode}
                        icon={<Icon name="Play" />}
                        title="Run Python Code"
                        disabled={!isEditable}
                    >
                        Run
                    </AsyncButton>
                </div>
                <BoundQueryEditor
                    value={context}
                    onChange={this.handleCodeChange}
                    readOnly={!isEditable}
                    language="python"
                />
            </div>
        );
    }
}

const mapStateToProps = (state: IStoreState) => ({
    // Add any necessary state mappings
});

const mapDispatchToProps = {
    createQueryExecution,
};

export const DataDocPythonCell = connect(
    mapStateToProps,
    mapDispatchToProps
)(DataDocPythonCellComponent);