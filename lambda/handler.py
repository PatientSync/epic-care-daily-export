import json
import os
import boto3
import csv
import io
import base64
import urllib.request
import urllib.parse
import time
from datetime import datetime, timedelta

# Initialize AWS clients
redshift_data = boto3.client('redshift-data', region_name='us-east-1')
secretsmanager = boto3.client('secretsmanager', region_name='us-east-1')

# Environment variables
CLUSTER_IDENTIFIER = os.environ['REDSHIFT_CLUSTER_IDENTIFIER']
DATABASE_NAME = os.environ['REDSHIFT_DATABASE_NAME']
DB_USER = os.environ['REDSHIFT_DB_USER']
REDSHIFT_SECRET_ARN = os.environ['REDSHIFT_SECRET_ARN']
GRAPH_CLIENT_ID = os.environ['GRAPH_CLIENT_ID']
GRAPH_CLIENT_SECRET = os.environ['GRAPH_CLIENT_SECRET']
GRAPH_TENANT_ID = os.environ['GRAPH_TENANT_ID']
FROM_EMAIL = os.environ['FROM_EMAIL']
TO_EMAIL = os.environ['TO_EMAIL']
BCC_EMAIL = os.environ.get('BCC_EMAIL', '')  # Optional BCC recipient


def get_access_token():
    """Authenticate with Microsoft Graph API and return access token"""
    token_endpoint = f"https://login.microsoftonline.com/{GRAPH_TENANT_ID}/oauth2/v2.0/token"
    
    post_data = {
        'client_id': GRAPH_CLIENT_ID,
        'client_secret': GRAPH_CLIENT_SECRET,
        'scope': 'https://graph.microsoft.com/.default',
        'grant_type': 'client_credentials'
    }
    
    data = urllib.parse.urlencode(post_data).encode('utf-8')
    req = urllib.request.Request(token_endpoint, data=data, method='POST')
    
    with urllib.request.urlopen(req) as response:
        response_data = json.loads(response.read().decode('utf-8'))
        
        if 'access_token' not in response_data:
            raise Exception(f"Failed to get access token: {response_data}")
        
        return response_data['access_token']


def execute_redshift_query():
    """Execute the Redshift query and return results"""
    query = """
    SELECT
      -- Timestamps formatted like: 2025-12-15T17:13:49.0000000
      CASE WHEN acw_end_tstamp IS NULL THEN NULL
           ELSE to_char(acw_end_tstamp, 'YYYY-MM-DD"T"HH24:MI:SS') || '.0000000' END AS acw_end_tstamp,
      CASE WHEN acw_start_tstamp IS NULL THEN NULL
           ELSE to_char(acw_start_tstamp, 'YYYY-MM-DD"T"HH24:MI:SS') || '.0000000' END AS acw_start_tstamp,

      aws_account_id,
      aws_ctr_format_ver,
      channel,

      CASE WHEN conn_to_agent_tstamp IS NULL THEN NULL
           ELSE to_char(conn_to_agent_tstamp, 'YYYY-MM-DD"T"HH24:MI:SS') || '.0000000' END AS conn_to_agent_tstamp,
      CASE WHEN conn_to_ac_tstamp IS NULL THEN NULL
           ELSE to_char(conn_to_ac_tstamp, 'YYYY-MM-DD"T"HH24:MI:SS') || '.0000000' END AS conn_to_ac_tstamp,

      contact_id,
      orig_contact_id,

      CASE WHEN ctr_init_tstamp IS NULL THEN NULL
           ELSE to_char(ctr_init_tstamp, 'YYYY-MM-DD"T"HH24:MI:SS') || '.0000000' END AS ctr_init_tstamp,

      cust_addr_type,
      cust_addr_val,

      CASE WHEN dequeue_tstamp IS NULL THEN NULL
           ELSE to_char(dequeue_tstamp, 'YYYY-MM-DD"T"HH24:MI:SS') || '.0000000' END AS dequeue_tstamp,
      CASE WHEN disc_tstamp IS NULL THEN NULL
           ELSE to_char(disc_tstamp, 'YYYY-MM-DD"T"HH24:MI:SS') || '.0000000' END AS disc_tstamp,
      CASE WHEN enqueue_tstamp IS NULL THEN NULL
           ELSE to_char(enqueue_tstamp, 'YYYY-MM-DD"T"HH24:MI:SS') || '.0000000' END AS enqueue_tstamp,

      handle_attempts,
      handled_by_agent,
      hold_dur,

      CASE WHEN last_upd_tstamp IS NULL THEN NULL
           ELSE to_char(last_upd_tstamp, 'YYYY-MM-DD"T"HH24:MI:SS') || '.0000000' END AS last_upd_tstamp,

      ac_addr_type,
      ac_addr_val,
      num_of_holds,
      instance_arn,
      prev_contact_id,
      queue,
      rec_loc,
      tlk_duration,
      ctr_init_method,
      next_contact_id,
      rec_del_reason,
      rec_status,
      rec_type,
      queue_duration,
      acw_duration,
      agent_arn,
      agent_hierarchy_1_name,
      agent_hierarchy_2_name,
      agent_hierarchy_3_name,
      agent_hierarchy_4_name,
      agent_hierarchy_5_name,
      routing_profile_name,

      CASE WHEN transfer_complete_time IS NULL THEN NULL
           ELSE to_char(transfer_complete_time, 'YYYY-MM-DD"T"HH24:MI:SS') || '.0000000' END AS transfer_complete_time,

      transfer_to_type,

      -- match old: strip leading '+' when present
      CASE
        WHEN transfer_to_val LIKE '+%' THEN SUBSTRING(transfer_to_val, 2)
        ELSE transfer_to_val
      END AS transfer_to_val,

      recording_del_reason,
      recording_location,
      recording_status,
      recording_type,
      related_id,
      task_name,
      task_description,
      amd_status,
      campaign_id,
      disc_reason,
      tag_clientid,
      tag_accountid,

      -- match old: strip leading '+' when present
      CASE
        WHEN tag_systemendpoint LIKE '+%' THEN SUBSTRING(tag_systemendpoint, 2)
        ELSE tag_systemendpoint
      END AS tag_systemendpoint,

      -- match old: lowercase agent name fields
      SPLIT_PART(LOWER(agent_full_name), ' ', 1) AS agent_first_name,
      TRIM(
        SUBSTRING(
          LOWER(agent_full_name)
          FROM POSITION(' ' IN LOWER(agent_full_name)) + 1
        )
      ) AS agent_last_name,
      LOWER(agent_full_name) AS agent_name,

      -- EPIC canonical ct set; everything else collapses to Other
CASE
  WHEN call_type = 'InboundHandledCall' THEN 'InboundHandledCall'
  WHEN call_type IN ('OutboundHandled', 'OutboundHandledCall') THEN 'OutboundHandled'
  WHEN call_type = 'Abandoned' THEN 'Abandoned'
  WHEN call_type = 'Callback' THEN 'Callback'          -- only this stays Callback
  WHEN call_type IN ('VM', 'Voicemail') THEN 'VM'
  ELSE 'Other'                                         -- CallbackPresented falls here
END AS ct
,

      calculated_disposition AS disposition

    FROM public.ctr_v3
    WHERE clientidentifier = 'Epic'
      AND last_upd_tstamp >= DATE_TRUNC('day', GETDATE()) - INTERVAL '1 day'
      AND last_upd_tstamp <  DATE_TRUNC('day', GETDATE())
      AND queue IS NOT NULL;
    """
    
    # Execute query using Redshift Data API
    # Try using DbUser first (for IAM/temporary credentials), fallback to SecretArn if needed
    try:
        # Use DbUser for temporary credentials/IAM authentication
        response = redshift_data.execute_statement(
            ClusterIdentifier=CLUSTER_IDENTIFIER,
            Database=DATABASE_NAME,
            DbUser=DB_USER,
            Sql=query
        )
    except Exception as e:
        # If DbUser fails, try with SecretArn (secret should contain username and password)
        if 'SecretArn' in str(e) or 'secret' in str(e).lower():
            raise  # Re-raise if it's already a secret error
        print(f"DbUser method failed: {str(e)}, trying with SecretArn...")
        response = redshift_data.execute_statement(
            ClusterIdentifier=CLUSTER_IDENTIFIER,
            Database=DATABASE_NAME,
            SecretArn=REDSHIFT_SECRET_ARN,
            Sql=query
        )
    
    statement_id = response['Id']
    
    # Poll for query completion
    max_attempts = 60
    attempt = 0
    while attempt < max_attempts:
        status_response = redshift_data.describe_statement(Id=statement_id)
        status = status_response['Status']
        
        if status == 'FINISHED':
            break
        elif status == 'FAILED' or status == 'ABORTED':
            error = status_response.get('Error', 'Unknown error')
            raise Exception(f"Query failed with status {status}: {error}")
        
        time.sleep(2)
        attempt += 1
    
    if attempt >= max_attempts:
        raise Exception("Query timed out")
    
    # Get query results
    results = []
    next_token = None
    
    while True:
        if next_token:
            result_response = redshift_data.get_statement_result(Id=statement_id, NextToken=next_token)
        else:
            result_response = redshift_data.get_statement_result(Id=statement_id)
        
        # Process results
        for record in result_response['Records']:
            row = []
            for field in record:
                # Handle different field types
                if 'stringValue' in field:
                    row.append(field['stringValue'])
                elif 'longValue' in field:
                    row.append(str(field['longValue']))
                elif 'doubleValue' in field:
                    row.append(str(field['doubleValue']))
                elif 'booleanValue' in field:
                    row.append(str(field['booleanValue']))
                elif 'isNull' in field and field['isNull']:
                    row.append('')
                else:
                    row.append('')
            results.append(row)
        
        next_token = result_response.get('NextToken')
        if not next_token:
            break
    
    # Get column names
    column_metadata = result_response['ColumnMetadata']
    column_names = [col['name'] for col in column_metadata]
    
    return column_names, results


def generate_csv(column_names, rows):
    """Generate CSV content from query results"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(column_names)
    
    # Write rows
    for row in rows:
        writer.writerow(row)
    
    return output.getvalue()


def send_email_with_attachment(csv_content, access_token):
    """Send email with CSV attachment using Microsoft Graph API"""
    # Encode CSV content as base64
    csv_bytes = csv_content.encode('utf-8')
    csv_base64 = base64.b64encode(csv_bytes).decode('utf-8')
    
    # Generate email subject with date
    yesterday = datetime.now() - timedelta(days=1)
    subject = f"EPIC Care Daily Export - {yesterday.strftime('%Y-%m-%d')}"
    
    # Build email message
    message_data = {
        "subject": subject,
        "body": {
            "contentType": "HTML",
            "content": f"""
            <html>
            <body>
                <p>Please find attached the daily export for {yesterday.strftime('%Y-%m-%d')}.</p>
                <p>This export contains contact center data from the previous day.</p>
            </body>
            </html>
            """
        },
        "toRecipients": [
            {
                "emailAddress": {
                    "address": TO_EMAIL
                }
            }
        ],
        "attachments": [
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": "EPICDW-XREF_PatSync.csv",
                "contentType": "text/csv",
                "contentBytes": csv_base64
            }
        ]
    }
    
    # Add BCC recipient if configured
    if BCC_EMAIL:
        message_data["bccRecipients"] = [
            {
                "emailAddress": {
                    "address": BCC_EMAIL
                }
            }
        ]
    
    message = {
        "message": message_data
    }
    
    # Send email via Graph API
    graph_endpoint = f"https://graph.microsoft.com/v1.0/users/{FROM_EMAIL}/sendMail"
    
    json_data = json.dumps(message).encode('utf-8')
    req = urllib.request.Request(
        graph_endpoint,
        data=json_data,
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        },
        method='POST'
    )
    
    with urllib.request.urlopen(req) as response:
        if response.status != 202:
            response_body = response.read().decode('utf-8')
            raise Exception(f"Failed to send email. Status: {response.status}, Response: {response_body}")


def lambda_handler(event, context):
    """Main Lambda handler"""
    try:
        print("Starting EPIC Care Daily Export process...")
        
        # Execute Redshift query
        print("Executing Redshift query...")
        column_names, results = execute_redshift_query()
        print(f"Query completed. Retrieved {len(results)} rows.")
        
        # Generate CSV
        print("Generating CSV file...")
        csv_content = generate_csv(column_names, results)
        print(f"CSV generated. Size: {len(csv_content)} bytes.")
        
        # Authenticate with Graph API
        print("Authenticating with Microsoft Graph API...")
        access_token = get_access_token()
        print("Authentication successful.")
        
        # Send email with attachment
        print("Sending email with CSV attachment...")
        send_email_with_attachment(csv_content, access_token)
        print("Email sent successfully.")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Daily export completed successfully',
                'rows_exported': len(results),
                'csv_size_bytes': len(csv_content)
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

