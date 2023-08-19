import React, { useState } from 'react';

import { QueryComparison } from 'components/TranspileQueryModal/QueryComparison';
import { AICommandType } from 'const/aiAssistant';
import { ComponentType, ElementType } from 'const/analytics';
import { useAISocket } from 'hooks/useAISocket';
import { trackClick } from 'lib/analytics';
import { trimSQLQuery } from 'lib/stream';
import { Button } from 'ui/Button/Button';
import { Message } from 'ui/Message/Message';
import { Modal } from 'ui/Modal/Modal';
import { AccentText } from 'ui/StyledText/StyledText';

import './AutoFixButton.scss';

interface IProps {
    query: string;
    queryExecutionId: number;
    onUpdateQuery?: (query: string, run?: boolean) => any;
}

export const AutoFixButton = ({
    query,
    queryExecutionId,
    onUpdateQuery,
}: IProps) => {
    const [show, setShow] = useState<boolean>(false);
    const [data, setData] = useState<{ [key: string]: string }>({});

    const socket = useAISocket(AICommandType.SQL_FIX, ({ data }) => {
        setData(data);
    });

    const {
        explanation,
        fix_suggestion: suggestion,
        fixed_query: rawFixedQuery,
    } = data;

    const fixedQuery = trimSQLQuery(rawFixedQuery);

    const bottomDOM = socket.loading ? (
        <div className="right-align mb16">
            <Button
                title="Stop Generating"
                color="light"
                onClick={socket.cancel}
                className="mr8"
            />
        </div>
    ) : (
        fixedQuery && (
            <div className="right-align mb16">
                <Button
                    title="Reject"
                    onClick={() => {
                        setShow(false);
                    }}
                />
                <Button
                    title="Apply"
                    color="confirm"
                    onClick={() => {
                        onUpdateQuery?.(fixedQuery, false);
                        trackClick({
                            component: ComponentType.AI_ASSISTANT,
                            element:
                                ElementType.QUERY_ERROR_AUTO_FIX_APPLY_BUTTON,
                        });
                        setShow(false);
                    }}
                />
                <Button
                    title="Apply and Run"
                    color="accent"
                    onClick={() => {
                        onUpdateQuery?.(fixedQuery, true);
                        trackClick({
                            component: ComponentType.AI_ASSISTANT,
                            element:
                                ElementType.QUERY_ERROR_AUTO_FIX_APPLY_AND_RUN_BUTTON,
                        });
                        setShow(false);
                    }}
                />
            </div>
        )
    );
    return (
        <>
            <Button
                icon="Bug"
                title="Auto fix"
                onClick={() => {
                    setShow(true);
                    if (Object.keys(data).length === 0) {
                        socket.emit({
                            query_execution_id: queryExecutionId,
                        });
                        trackClick({
                            component: ComponentType.AI_ASSISTANT,
                            element: ElementType.QUERY_ERROR_AUTO_FIX_BUTTON,
                            aux: {
                                queryExecutionId,
                            },
                        });
                    }
                }}
            />
            {show && (
                <Modal
                    onHide={() => {
                        socket.cancel();
                        setShow(false);
                    }}
                    bottomDOM={bottomDOM}
                    className="AutoFixModal"
                >
                    <Message
                        message="Note: This AI-powered auto fix may not be 100% accurate. Please use your own judgement and verify the result."
                        type="warning"
                    />
                    {explanation && (
                        <div>
                            <AccentText size="med" weight="bold">
                                Explanation
                            </AccentText>
                            <AccentText>{explanation}</AccentText>
                        </div>
                    )}
                    {suggestion && (
                        <div className="mt16">
                            <AccentText size="med" weight="bold">
                                Suggestion
                            </AccentText>
                            <AccentText>{suggestion}</AccentText>
                        </div>
                    )}
                    {fixedQuery && (
                        <div style={{ marginTop: 16 }}>
                            <QueryComparison
                                fromQuery={query}
                                toQuery={fixedQuery}
                                fromQueryTitle="Original"
                                toQueryTitle="Fixed"
                                disableHighlight={socket.loading}
                            />
                        </div>
                    )}
                </Modal>
            )}
        </>
    );
};
