# Plan: Multi-User Role System with Customer Profiles

Add role-based access control (RBAC) with two user types: **Admin** (full file upload/management permissions) and **Customer** (view-only access to their files + general-use files). Admins can create customer profiles and upload files organized by customer ID in S3 with a separate `general/` folder for shared content.

## Steps

1. **Extend Cognito with User Groups and Custom Attributes** in `terraform/cognito.tf`: Create `Admins` and `Customers` groups, add custom `customer_id` attribute to user schema, and update IAM policy in `terraform/iam.tf` to allow admin operations (`AdminCreateUser`, `AdminAddUserToGroup`, `AdminSetUserPassword`).

2. **Create Customer Profile Management** by adding new Pydantic models in `api/models/__init__.py` (`CreateCustomerRequest`, `CustomerProfileResponse`, `UpdateCustomerRequest`) and implementing `CognitoAuth.create_customer()` and `CognitoAuth.list_customers()` methods in `api/services/auth.py`.

3. **Implement Role-Based Authorization Middleware** in `api/services/auth.py`: Create `require_admin()` and `require_customer()` dependency functions that check `cognito:groups` claim from JWT tokens, extracting user role and customer_id from verified tokens.

4. **Refactor S3 Service for Customer-Based Organization** in `api/services/s3.py`: Update `_generate_s3_key()` to use prefix structure `customers/{customer_id}/` or `general/`, modify `upload_image()` to accept `customer_id` parameter, and implement `list_images_for_customer()` that filters by customer prefix + general folder.

5. **Add Admin-Only Customer Management Endpoints** in new file `api/routers/customers.py`: Create POST `/customers` (create customer profile), GET `/customers` (list all), GET `/customers/{customer_id}` (get details), and PATCH `/customers/{customer_id}` (update profile), all protected by `require_admin()`.

6. **Update Image Upload/List Endpoints** in `api/routers/images.py`: Modify POST `/images/upload` to accept optional `customer_id` (admin-only) or use authenticated customer's ID, update GET `/images/list` to filter results based on user role (admins see all, customers see their files + general), and add admin-only DELETE protection.

7.  **Customer Profile Storage**: Use Cognito custom attributes only to begin with, we will add richer metadata storage in DynamoDB later if needed.

8. **Use Single S3 Bucket with Folder Prefixes**: Store all files in one bucket using prefixes  (`customers/{id}/`, `general/`) for customer-specific and general files for cost efficiency.

9. **Customer Invitation Flow**: Admins generate temporary passwords for new customers initially, with plans to enhance with email invitations and password setup links using Cognito triggers in the future.
