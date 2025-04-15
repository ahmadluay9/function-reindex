# Import necessary libraries
import functions_framework
from google.cloud import discoveryengine
from google.api_core.client_options import ClientOptions
import os
from dotenv import load_dotenv

# load .env file to environment
load_dotenv()

# Define constants for Discovery Engine - Consider using environment variables for production
# You can set these in the Cloud Function's environment variables settings
PROJECT_ID = os.environ.get("PROJECT_ID") # Your Google Cloud project ID
LOCATION = os.environ.get("LOCATION") # Location of your Discovery Engine datastore (e.g., "global", "us")
DATASTORE_ID = os.environ.get("DATASTORE_ID") # Your Discovery Engine datastore ID

# Triggered by a change in a specific storage bucket (configure this in Cloud Function settings)
@functions_framework.cloud_event
def import_document_on_gcs_event(cloud_event):
    """
    Google Cloud Function triggered by a GCS event to import the triggering
    document into a Discovery Engine datastore.
    """
    # Extract data from the GCS event
    data = cloud_event.data

    # Get details of the file that triggered the event
    bucket_name = data.get("bucket")
    file_name = data.get("name")
    event_type = cloud_event["type"] # e.g., google.cloud.storage.object.v1.finalized

    # Log basic event information
    print(f"Event type: {event_type}")
    print(f"Bucket: {bucket_name}")
    print(f"File: {file_name}")

    # Proceed only if it's a file creation/update event and file name exists
    if not file_name or not bucket_name:
        print("No file name or bucket name found in the event data. Exiting.")
        return

    # Construct the GCS URI for the specific file that triggered the event
    gcs_uri = f"gs://{bucket_name}/{file_name}"
    print(f"Constructed GCS URI: {gcs_uri}")

    # --- Document Import Logic ---
    try:
        # Configure the API endpoint based on the location
        client_options = (
            ClientOptions(api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com")
            if LOCATION != "global"
            else None
        )

        # Create a Discovery Engine Document Service client
        client = discoveryengine.DocumentServiceClient(client_options=client_options)

        # Construct the full resource name of the parent branch
        parent = client.branch_path(
            project=PROJECT_ID,
            location=LOCATION,
            data_store=DATASTORE_ID,
            branch="default_branch",  # Use the default branch
        )

        # Prepare the import request
        request = discoveryengine.ImportDocumentsRequest(
            parent=parent,
            gcs_source=discoveryengine.GcsSource(
                input_uris=[gcs_uri],  # Import the specific file
                data_schema="content", # Assumes the content schema
            ),
            # Use INCREMENTAL to add/update the document, or FULL for complete refresh
            reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
        )

        # Initiate the import documents operation
        print(f"Starting document import for: {gcs_uri}")
        operation = client.import_documents(request=request)

        # Wait for the operation to complete and print results
        print(f"Waiting for import operation to complete: {operation.operation.name}")
        response = operation.result() # This blocks until the operation is done

        # Extract metadata after the operation is complete
        metadata = discoveryengine.ImportDocumentsMetadata(operation.metadata)

        # Log the response and metadata
        print("Import operation response:")
        print(response)
        print("Import operation metadata:")
        print(metadata)
        print(f"Successfully imported {gcs_uri} into datastore {DATASTORE_ID}")

    except Exception as e:
        # Log any errors encountered during the import process
        print(f"Error importing document {gcs_uri}: {e}")
