# Infrastructure Deployment Summary

## Deployment Date
2026-06-27

## Successfully Deployed Resources

### DynamoDB Tables

1. **ai-swim-coach-users**
   - Purpose: User authentication credentials and profile picture URLs
   - Partition Key: `user_id` (String)
   - GSI: `email-index` (for login lookups)
   - Billing: PAY_PER_REQUEST

2. **ai-swim-coach-user-profiles**
   - Purpose: User demographic and ability profile data
   - Partition Key: `user_id` (String)
   - Billing: PAY_PER_REQUEST

3. **ai-swim-coach-sessions**
   - Purpose: Historical swim session data with metrics
   - Partition Key: `user_id` (String)
   - Sort Key: `session_date` (String, ISO 8601 format)
   - GSI: `session_id-index` (for direct session lookups)
   - Billing: PAY_PER_REQUEST

4. **coaching-sessions** (existing)
   - Purpose: Coaching responses for auditing
   - Partition Key: `file_key` (String)
   - Sort Key: `created_at` (String)

### S3 Buckets

1. **ai-swim-coach-profile-pictures-20260627190447900400000001**
   - Purpose: User profile picture storage
   - Access: Public read enabled
   - CORS: Configured for web uploads (GET, POST, PUT)
   - Policy: Public read access for all objects

2. **ai-swim-coach-uploads-20260627160113311500000001** (existing)
   - Purpose: Raw FIT file storage
   - Access: Private (Lambda only)

### Lambda Function Updates

**ai-swim-coach**
- Updated environment variables:
  - `S3_BUCKET`: ai-swim-coach-uploads-20260627160113311500000001
  - `DYNAMODB_TABLE`: coaching-sessions
  - `PROFILE_PICTURES_BUCKET`: ai-swim-coach-profile-pictures-20260627190447900400000001
  - `USERS_TABLE`: ai-swim-coach-users
  - `PROFILES_TABLE`: ai-swim-coach-user-profiles
  - `SESSIONS_TABLE`: ai-swim-coach-sessions
  - `JWT_SECRET`: [SECURED - 256-bit secret for JWT signing]

### IAM Permissions Updates

Lambda execution role now has access to:
- **Users table**: PutItem, GetItem, UpdateItem, Query (including email-index GSI)
- **UserProfiles table**: PutItem, GetItem, UpdateItem
- **Sessions table**: PutItem, GetItem, Query (including session_id-index GSI)
- **Profile pictures bucket**: PutObject, GetObject, DeleteObject

## Resource ARNs

- Users Table: `arn:aws:dynamodb:us-east-1:562535532900:table/ai-swim-coach-users`
- Profiles Table: `arn:aws:dynamodb:us-east-1:562535532900:table/ai-swim-coach-user-profiles`
- Sessions Table: `arn:aws:dynamodb:us-east-1:562535532900:table/ai-swim-coach-sessions`
- Profile Pictures Bucket: `arn:aws:s3:::ai-swim-coach-profile-pictures-20260627190447900400000001`

## Endpoints

- **API Gateway**: https://lp84bjpr2c.execute-api.us-east-1.amazonaws.com/prod
- **Frontend (Amplify)**: https://main.d3qbayea55l8tl.amplifyapp.com

## Next Steps

1. **Backend Development**:
   - Implement authentication module (`backend/auth.py`)
   - Implement HR zones module (`backend/hr_zones.py`)
   - Implement profile manager (`backend/profile_manager.py`)
   - Implement session history module (`backend/session_history.py`)
   - Update handler.py with new routes

2. **Frontend Development**:
   - Implement login/registration components
   - Implement profile management UI
   - Implement session history and calendar views
   - Add HR zones visualization
   - Add ability assessment display

3. **Testing**:
   - Test user registration and login flows
   - Test profile creation and updates
   - Test profile picture upload
   - Test session storage and retrieval
   - Test HR zone calculations

## Cost Impact

Estimated additional monthly costs (for typical usage):
- DynamoDB (3 new tables, PAY_PER_REQUEST): < $1.00
- S3 storage (profile pictures): ~$0.023/GB
- S3 requests: minimal
- Lambda: no significant change (same function, more env vars)

**Total estimated additional cost**: < $5.00/month

## Security Notes

- JWT secret is securely stored in terraform.tfvars (not committed to git)
- Profile pictures bucket has public read access (intentional for direct image loading)
- All other resources maintain private access
- Lambda has minimum required permissions for each table/bucket

## Verification Commands

```bash
# List DynamoDB tables
aws dynamodb list-tables

# Check Users table
aws dynamodb describe-table --table-name ai-swim-coach-users

# Check Sessions table
aws dynamodb describe-table --table-name ai-swim-coach-sessions

# List S3 buckets
aws s3 ls | grep ai-swim-coach

# Check Lambda environment variables
aws lambda get-function-configuration --function-name ai-swim-coach | jq '.Environment.Variables'
```

## Rollback Instructions

If you need to rollback these changes:

```bash
cd infra
terraform destroy -target=aws_dynamodb_table.users
terraform destroy -target=aws_dynamodb_table.user_profiles
terraform destroy -target=aws_dynamodb_table.sessions
terraform destroy -target=aws_s3_bucket.profile_pictures
```

Note: This will delete all data in these tables. Backup any important data before rolling back.
