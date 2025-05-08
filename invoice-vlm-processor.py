import os
import json
import asyncio
import tempfile
from llama_stack_client import LlamaStackClient
from dotenv import load_dotenv
import logging
import base64
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError, PDFSyntaxError
from models import InvoiceObject
import aioboto3

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ----- Configuration from Environment -----
ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
REGION       = os.getenv("S3_DEFAULT_REGION", "us-east-1")
ACCESS_KEY   = os.getenv("S3_ACCESS_KEY_ID")
SECRET_KEY   = os.getenv("S3_SECRET_ACCESS_KEY")

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 3))

SOURCE_BUCKET = "invoices"
ERROR_PREFIX  = "error/"      # Prefix for files that failed processing
PDF_INPUT   = "done/"       # Prefix for retrieving PDF input
PNG_OUTPUT   = "png/"     # Prefix for storing PNG output
JSON_OUTPUT   = "json-header/"     # Prefix for storing JSON output
PROCESSED_PREFIX = "processed/"  # Prefix for processed PDF files


LLAMA_STACK_SERVER=os.getenv("LLAMA_STACK_SERVER")
LLAMA_STACK_VISION_MODEL="ibm-granite/granite-vision-3.2-2b"

logger.info(f"ENDPOINT_URL: {ENDPOINT_URL}")
logger.info(f"REGION: {REGION}")
logger.info(f"ACCESS_KEY: {ACCESS_KEY}")
logger.info(f"SECRET_KEY: {SECRET_KEY}")
logger.info(f"POLL_INTERVAL: {POLL_INTERVAL}")
logger.info(f"SOURCE_BUCKET: {SOURCE_BUCKET}")
logger.info(f"ERROR_PREFIX: {ERROR_PREFIX}")
logger.info(f"PDF_INPUT: {PDF_INPUT}")
logger.info(f"PNG_OUTPUT: {PNG_OUTPUT}")
logger.info(f"JSON_OUTPUT: {JSON_OUTPUT}")
logger.info(f"LLAMA_STACK_SERVER: {LLAMA_STACK_SERVER}")
logger.info(f"LLAMA_STACK_VISION_MODEL: {LLAMA_STACK_VISION_MODEL}")

client = LlamaStackClient(base_url=os.getenv("LLAMA_STACK_SERVER"))

def convert_pdf_to_png(pdf_path):
    logger.info(f"Converting PDF to PNG: {pdf_path}")
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        return

    try:
        print(f"Converting {pdf_path} to PNG images...")
        # Convert PDF to a list of PIL images
        images = convert_from_path(pdf_path)

        # Get the base name of the PDF file without extension
        base_filename = os.path.splitext(os.path.basename(pdf_path))[0]

        # Extract the directory from pdf_path
        output_dir = os.path.dirname(pdf_path)
        if output_dir == '':
            output_dir = '.'  # Use current directory if no directory in path


        # Save each image as a PNG file
        for i, image in enumerate(images):
            output_filename = os.path.join(output_dir, f"{base_filename}_page_{i + 1}.png")
            image.save(output_filename, 'PNG')
            print(f"Saved page {i + 1} to {output_filename}")
            return output_filename

        print("Conversion complete.")

    except PDFInfoNotInstalledError:
        print("Error: pdf2image requires poppler to be installed and in PATH.")
        print("Please install poppler:")
        print("  macOS (brew): brew install poppler")
        print("  Debian/Ubuntu: sudo apt-get install poppler-utils")
        print("  Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/")
    except PDFPageCountError:
        print(f"Error: Could not get page count for {pdf_path}. Is it a valid PDF?")
    except PDFSyntaxError:
        print(f"Error: PDF file {pdf_path} seems to be corrupted or invalid.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        base64_string = base64.b64encode(image_file.read()).decode("utf-8")        
        return base64_string



def process_invoice(image_path):
    invoice_object = InvoiceObject()
    try:        
        # Invoice Number
        response = client.inference.chat_completion(
        model_id=LLAMA_STACK_VISION_MODEL,
        messages=[
        # {"role": "system", "content": "You are an expert image analyzer"},
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": {
                        "data": encode_image(image_path)
                    }
                },
                {
                    "type": "text",
                    "text": "what is the invoice number and only the invoice number",
                }
            ]
            }
        ],        
        )
        logger.info(response.completion_message.content)
        invoice_number = response.completion_message.content
        invoice_object.invoice_number = invoice_number

        # Invoice Date
        response = client.inference.chat_completion(
        model_id=LLAMA_STACK_VISION_MODEL,
        messages=[
        # {"role": "system", "content": "You are an expert image analyzer"},
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": {
                        "data": encode_image(image_path)
                    }
                },
                {
                    "type": "text",
                    "text": "what is the invoice date and only the invoice date",
                }
            ]
            }
        ],        
        )
        logger.info(response.completion_message.content)
        invoice_date = response.completion_message.content
        invoice_object.invoice_date = invoice_date

        # Seller Name
        response = client.inference.chat_completion(
        model_id=LLAMA_STACK_VISION_MODEL,
        messages=[
        # {"role": "system", "content": "You are an expert image analyzer"},
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": {
                        "data": encode_image(image_path)
                    }
                },
                {
                    "type": "text",
                    "text": "what is seller's name",
                }
            ]
            }
        ],        
        )
        logger.info(response.completion_message.content)
        seller_name = response.completion_message.content
        invoice_object.seller = seller_name

        response = client.inference.chat_completion(
        model_id=LLAMA_STACK_VISION_MODEL,
        messages=[
        # {"role": "system", "content": "You are an expert image analyzer"},
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": {
                        "data": encode_image(image_path)
                    }
                },
                {
                    "type": "text",
                    "text": "what is seller's tax id",
                }
            ]
            }
        ],        
        )
        logger.info(response.completion_message.content)
        seller_tax_id = response.completion_message.content
        invoice_object.seller_tax_id = seller_tax_id


        return invoice_object
    except Exception as e:
        logger.error(f"Error processing invoice: {e}")
        return None

def create_s3_client():
    """Create and return an aioboto3 S3 client using environment variables."""
    session = aioboto3.Session()
    return session.client(
        's3',
        endpoint_url=ENDPOINT_URL,
        region_name=REGION,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY
    )

async def list_pdf_files(s3_client):
    """List PDF files in the 'invoices/done' prefix."""
    try:
        response = await s3_client.list_objects_v2(
            Bucket=SOURCE_BUCKET,
            Prefix=PDF_INPUT
        )
        
        if 'Contents' not in response:
            return []
            
        return [obj['Key'] for obj in response['Contents']
                if obj['Key'].lower().endswith('.pdf')]
    except Exception as e:
        logger.error(f"Error listing PDF files: {e}")
        return []

async def download_file(s3_client, bucket, key, local_path):
    """Download a file from S3 to local storage."""
    try:
        await s3_client.download_file(bucket, key, local_path)
        logger.info(f"Downloaded {key} to {local_path}")
        return local_path
    except Exception as e:
        logger.error(f"Error downloading {key}: {e}")
        raise

async def upload_file(s3_client, local_path, bucket, key):
    """Upload a file from local storage to S3."""
    try:
        await s3_client.upload_file(local_path, bucket, key)
        logger.info(f"Uploaded {local_path} to {bucket}/{key}")
        return key
    except Exception as e:
        logger.error(f"Error uploading {local_path} to {bucket}/{key}: {e}")
        raise

async def move_s3_object(s3_client, bucket, source_key, dest_key):
    """Move an object from source_key to dest_key."""
    try:
        # Copy the object
        copy_source = {'Bucket': bucket, 'Key': source_key}
        await s3_client.copy_object(
            CopySource=copy_source,
            Bucket=bucket,
            Key=dest_key
        )
        logger.info(f"Copied {source_key} to {dest_key}")
        
        # Delete the original
        await s3_client.delete_object(Bucket=bucket, Key=source_key)
        logger.info(f"Deleted {source_key}")
        
        return dest_key
    except Exception as e:
        logger.error(f"Error moving {source_key} to {dest_key}: {e}")
        raise

async def process_pdf(s3_client, bucket, key):
    """Process a PDF file from S3."""
    # Create a temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Download the PDF
            pdf_filename = os.path.basename(key)
            local_pdf_path = os.path.join(temp_dir, pdf_filename)
            await download_file(s3_client, bucket, key, local_pdf_path)
            
            # Convert PDF to PNG
            local_png_path = convert_pdf_to_png(local_pdf_path)
            if not local_png_path:
                raise Exception(f"Failed to convert {pdf_filename} to PNG")
            
            # Upload PNG to S3
            png_filename = os.path.basename(local_png_path)
            png_key = f"{PNG_OUTPUT}{png_filename}"
            await upload_file(s3_client, local_png_path, bucket, png_key)
            
            # Process the PNG with VLM
            invoice_object = process_invoice(local_png_path)
            if not invoice_object:
                raise Exception(f"Failed to process {png_filename}")
            
            # Serialize to JSON
            json_content = invoice_object.model_dump_json()
            json_filename = os.path.splitext(png_filename)[0] + ".json"
            local_json_path = os.path.join(temp_dir, json_filename)
            
            with open(local_json_path, 'w') as f:
                f.write(json_content)
            
            # Upload JSON to S3
            json_key = f"{JSON_OUTPUT}{json_filename}"
            await upload_file(s3_client, local_json_path, bucket, json_key)
            
            # Move PDF to processed prefix
            processed_key = key.replace(PDF_INPUT, PROCESSED_PREFIX)
            await move_s3_object(s3_client, bucket, key, processed_key)
            
            logger.info(f"Successfully processed {pdf_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing {key}: {e}")
            
            # Move PDF to error prefix
            try:
                error_key = key.replace(PDF_INPUT, ERROR_PREFIX)
                await move_s3_object(s3_client, bucket, key, error_key)
            except Exception as move_error:
                logger.error(f"Error moving {key} to error prefix: {move_error}")
            
            return False

async def main():
    """Main function to run the continuous polling loop."""
    logger.info("Starting invoice processor")
    
    while True:
        try:
            # Create S3 client
            async with create_s3_client() as client:
                # List PDF files
                pdf_files = await list_pdf_files(client)
                
                if pdf_files:
                    logger.info(f"Found {len(pdf_files)} PDF files to process")
                    
                    # Process one file at a time
                    for pdf_key in pdf_files:
                        await process_pdf(client, SOURCE_BUCKET, pdf_key)
                else:
                    logger.info("No PDF files found to process")
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        
        # Wait for the next polling interval
        logger.info(f"Waiting {POLL_INTERVAL} seconds before next poll")
        await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())

