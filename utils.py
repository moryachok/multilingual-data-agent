import struct
import urllib
from azure import identity
from itertools import chain, repeat
import os
import sqlalchemy as sa
from semantic_kernel.functions import kernel_function
import pandas as pd
from semantic_kernel.contents import FunctionCallContent, FunctionResultContent
from semantic_kernel.contents.chat_message_content import ChatMessageContent
import logging

# Set up logging to file for this module
file_handler = logging.FileHandler("logs/streamlit_utils.log", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"))
logger = logging.getLogger("streamlit-utils")
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)

class FabricLakehousePlugin:
    def __init__(self, database):
        resource_url = "https://database.windows.net/.default"
        azure_credentials = identity.DefaultAzureCredential()
        token_object = azure_credentials.get_token(resource_url)
        
        sql_endpoint = os.getenv("FABRIC_SQL_ENDPOINT")
        connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};Server={sql_endpoint},1433;Database={database};Encrypt=Yes;TrustServerCertificate=No"
        params = urllib.parse.quote(connection_string)

        # Retrieve an access token
        token_as_bytes = bytes(token_object.token, "UTF-8") # Convert the token to a UTF-8 byte string
        encoded_bytes = bytes(chain.from_iterable(zip(token_as_bytes, repeat(0)))) # Encode the bytes to a Windows byte string
        token_bytes = struct.pack("<i", len(encoded_bytes)) + encoded_bytes # Package the token into a bytes object
        attrs_before = {1256: token_bytes}  # Attribute pointing to SQL_COPT_SS_ACCESS_TOKEN to pass access token to the driver
        self.engine = sa.create_engine("mssql+pyodbc:///?odbc_connect={0}".format(params), connect_args={'attrs_before': attrs_before})

    @kernel_function(
        description="Executes an SQL query on the insurance database and return the result as a string."
    )
    def run_query(self, query: str) -> str:
        print(query)
        logger.info(f"Executing query: {query}")
        logger.info(f"Query repr: {repr(query)}")
        try:
            df = pd.read_sql(query, self.engine)
            return df.to_string(index=False)
        except Exception as e:
            logger.error(f"Error running query: {e}")
            return f"Error: {e}"
        
async def handle_intermediate_steps(message: ChatMessageContent) -> None:
    for item in message.items or []:
        if isinstance(item, FunctionResultContent):
            print(f"Function Result:> {item.result} for function: {item.name}")
        elif isinstance(item, FunctionCallContent):
            print(f"Function Call:> {item.name} with arguments: {item.arguments}")
        else:
            print(f"{item}")