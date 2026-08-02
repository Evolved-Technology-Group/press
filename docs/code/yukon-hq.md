# Yukon HQ

Yukon HQ is ETG's business control-plane module inside the Press application.
It shares the Press site and database so the infrastructure record and the
commercial/support record cannot drift into separate systems. Its code remains
isolated under `press/hq` so upstream Press infrastructure updates stay
reviewable.

HQ currently owns:

- one tenant record linked to each managed Press Site;
- the Yukon Send plan catalogue and tenant subscription state;
- provider account and scoped-key provisioning;
- HaloPSA recurring-subscription synchronization;
- authenticated Yukon tenant support requests and HaloPSA ticket creation; and
- tenant configuration publication through Press's native Site job.

## Control-site configuration

Store secrets only in the Press control site's configuration. Do not publish
the delivery master key or Halo client secret to tenant sites.

```json
{
  "yukon_hq_public_url": "https://press.yukoncrm.com",
  "yukon_hq_smtp2go_api_key": "provider-master-key",
  "yukon_hq_halo_resource_url": "https://example.halopsa.com/api",
  "yukon_hq_halo_auth_url": "https://example.halopsa.com/auth/token",
  "yukon_hq_halo_client_id": "client-id",
  "yukon_hq_halo_client_secret": "client-secret",
  "yukon_hq_halo_ticket_type_id": 1,
  "yukon_hq_halo_ticket_url_template": "https://example.halopsa.com/tickets?id={ticket_id}",
  "yukon_support_url": "https://www.yukoncrm.com/support",
  "yukon_support_email": "support@yukoncrm.com"
}
```

`yukon_hq_halo_priority_ids` may map Yukon priorities (`Normal`, `High`, and
`Urgent`) to Halo priority IDs.

## Tenant onboarding

1. Create the customer and its site through normal Press operations.
2. Create an `HQ Tenant` linked to that Press Site and record its Halo client,
   optional site, and optional default user IDs.
3. Create the enabled `HQ Send Plan` rows. The monthly-send value must be one of
   the provider-supported account limits; the Halo subscription name must match
   the recurring invoice rule configured in Halo.
4. Call `press.api.hq.issue_tenant_token` as a System Manager. Copy the returned
   token only if the Site configuration job cannot run automatically.
5. Confirm the Site configuration job succeeded, then call
   `press.api.hq.retire_previous_tenant_token` after a credential rotation.

Press publishes only the plan catalogue, HQ endpoint URLs, and a per-tenant
bearer credential. A Yukon tenant never receives the provider master key or any
Halo credential.

## Tenant API contracts

Both tenant routes accept `POST` only and require
`X-Yukon-Tenant-Token: <tenant-token>`. A dedicated header is required because
Frappe reserves the standard Bearer authorization scheme for its OAuth tokens.
Yukon Send activation also requires a unique `Idempotency-Key` header. Support
requests use the durable tenant request name as their idempotency identifier.
Reusing an identifier with different content is rejected.

- `/api/method/press.api.hq.activate_yukon_send`
- `/api/method/press.api.hq.submit_support_request`

Activation is only reported as active after both the delivery subaccount and
the matching Halo subscription exist. Support is only reported as submitted
after Halo returns a ticket ID. Failed attempts stay visible in HQ and can be
retried with the same request identifier.
