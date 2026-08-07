# Configurable Data Backends

`AnalyticsService` depends on a common `QueryBackend` interface.

- **SQLiteBackend** keeps local development runnable.
- **AthenaBackend** uses AWS SDK / IAM.
- **SQLGatewayBackend** uses an internal regional gateway with `user_id` and token authentication.

The backend is selected by configuration instead of changing agent logic.
