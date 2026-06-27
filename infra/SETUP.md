# Infrastructure Setup Guide

This guide covers the setup of AWS infrastructure for the AI Swim Coach application, including authentication, user profiles, and session history features.

## Prerequisites

- Terraform >= 1.0
- AWS CLI configured with appropriate credentials
- AWS account with permissions for DynamoDB, S3, Lambda, API Gateway, and IAM

## Infrastructure Components

### DynamoDB Tables

1. **coaching-sessions**: Stores coaching responses for auditing
2. **ai-swim-coach-users**: User authentication credentials and profile picture URLs
   - Partition key: `user_id`
   - GSI: `email-index` for login lookups
3. **ai-swim-coach-user-profiles**: User demographic and ability profile data
   - Partition key: `user_id`
4. **ai-swim-coach-sessions**: Historical swim session data
   - Partition key: `user_id`
   - Sort key: `session_date`
   - GSI: `session_id-index` for direct session lookups

### S3 Buckets

1. **ai-swim-coach-uploads**: Raw FIT file storage (private)
2. **ai-swim-coach-profile-pictures**: User profile pictures (public read access)

### Environment Variables

The Lambda function requires the following environment variables:

- `S3_BUCKET`: FIT file uploads bucket
- `DYNAMODB_TABLE`: Coaching sessions table
- `PROFILE_PICTURES_BUCKET`: Profile pictures bucket
- `USERS_TABLE`: Users table name
- `PROFILES_TABLE`: User profiles table name
- `SESSIONS_TABLE`: Sessions table name
- `JWT_SECRET`: Secret key for JWT token signing (minimum 256-bit)

## Setup Instructions

### 1. Generate JWT Secret

Generate a secure JWT secret:

```bash
openssl rand -base64 32
```

### 2. Update terraform.tfvars

Replace the placeholder JWT secret in `terraform.tfvars`:

```hcl
jwt_secret = "your-generated-secret-here"
```

**Important**: Keep this secret secure and never commit it to version control in production. Consider using AWS Secrets Manager or environment variables for production deployments.

### 3. Initialize Terraform

```bash
cd infra
terraform init
```

### 4. Plan Infrastructure Changes

Review the planned changes:

```bash
terraform plan
```

You should see:
- 3 new DynamoDB tables (users, user_profiles, sessions)
- 1 new S3 bucket (profile-pictures) with public read policy
- Updated Lambda environment variables
- Updated IAM permissions for Lambda

### 5. Apply Infrastructure Changes

Apply the changes:

```bash
terraform apply
```

Type `yes` when prompted to confirm.

### 6. Verify Deployment

After successful deployment, verify the outputs:

```bash
terraform output
```

You should see outputs for all tables, buckets, and the Lambda function name.

## Security Considerations

### JWT Secret

- **Never** commit the JWT secret to version control
- Use a minimum 256-bit (32-byte) secret
- Rotate the secret periodically
- In production, use AWS Secrets Manager and reference it in Terraform

### Profile Pictures Bucket

- The profile pictures bucket has public read access to allow direct image loading
- Only authenticated users can upload pictures (controlled by Lambda)
- Consider adding CloudFront in front of the bucket for better performance and additional security options

### IAM Permissions

The Lambda function has been granted:
- Read/write access to all DynamoDB tables
- Read/write/delete access to profile pictures bucket
- Write access to uploads bucket
- Bedrock model invocation

## Testing

After deployment, test the infrastructure:

1. Test user registration: `POST /auth/register`
2. Test user login: `POST /auth/login`
3. Test profile creation: `POST /profile` (with JWT token)
4. Test profile picture upload: `POST /profile/picture` (with JWT token)
5. Test session storage: Upload a FIT file and verify session is saved

## Troubleshooting

### JWT_SECRET not set error

If you see errors about missing JWT_SECRET:
1. Ensure `terraform.tfvars` contains the `jwt_secret` variable
2. Run `terraform apply` again to update the Lambda environment

### DynamoDB table already exists

If tables already exist with the same names:
1. Either delete the existing tables (if safe to do so)
2. Or modify the table names in `dynamodb.tf`

### Profile pictures not accessible

If profile pictures return 403 errors:
1. Verify the bucket policy in `s3.tf` was applied correctly
2. Check the S3 bucket public access settings in AWS console
3. Ensure the Lambda function is storing the correct S3 URL format

## Cost Estimation

- **DynamoDB**: Pay-per-request pricing (typically < $1/month for low traffic)
- **S3**: Storage costs for profile pictures (~$0.023/GB/month)
- **Lambda**: Existing costs, no significant change
- **API Gateway**: Existing costs, no significant change

Total estimated additional cost: **< $5/month** for typical usage

## Next Steps

After infrastructure is set up:
1. Deploy updated Lambda function with authentication code
2. Update frontend with login/registration components
3. Test the complete authentication flow
4. Configure profile picture upload in the frontend
5. Implement session history UI components
