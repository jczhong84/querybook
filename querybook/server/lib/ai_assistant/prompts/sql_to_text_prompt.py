from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)


system_message_template = (
    "You are a helpful assistant that can help summarize SQL queries."
)

human_message_template = """
Please summarize below SQL query by given context. The summary will be used as a reference for table discovery and sql query generation, so please make it as informative as possible.
===Table Schemas
{table_schemas}

===SQL Query
{query}
"""

SQL_TO_TEXT_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(system_message_template),
        HumanMessagePromptTemplate.from_template(human_message_template),
    ]
)
