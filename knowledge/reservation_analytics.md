# Reservation Analytics Knowledge

## Business Scope

The business flow in this project is:

Reservation → Order

Payment is not part of this project.

The AI layer is added on top of the existing Reservation Analytics Data Mart. It does not redesign the Data Mart.

## Business Definitions

### Reserved User

A Reserved User is a distinct user who has a valid reservation record for the resolved campaign context.

### Ordered User

An Ordered User is a distinct reserved user who has a corresponding order in the approved campaign analysis window.

### Reserved-but-not-ordered User

A Reserved-but-not-ordered User is a user who has a reservation for the selected campaign context but has no corresponding order within the approved campaign analysis window.

This segment can be used by CRM or operations teams for follow-up analysis and targeting.

## Metric Definitions

### Reserved Users

Count of distinct users where `reserve_flag = 1` for the resolved campaign context.

### Ordered Users

Count of distinct users where `order_flag = 1` for the resolved campaign context.

### Reserved-but-not-ordered Users

Count of distinct users where `tag_reserved_not_paid = 1`.

The existing field name is preserved from the Data Mart implementation even though the business flow in this project is Reservation → Order and does not include a Payment dataset.

### Reservation-to-Order Conversion Rate

Reservation-to-Order Conversion Rate = Ordered Users / Reserved Users

The numerator and denominator must use the same campaign, product, site, and approved campaign analysis period.

## Data Mart

### Core Table

`reservation_dm.dm_reservation_conversion`

### Grain

User × Campaign × Product × Site

One row represents one user's activity for one campaign, one product, and one site.

### Important Fields

- `user_id`: user identifier
- `campaign_id`: resolved campaign identifier
- `product_id`: product identifier
- `site`: site context
- `reserve_time`: reservation timestamp
- `reserve_flag`: reservation indicator
- `order_flag`: order indicator
- `tag_reserved_not_paid`: existing DM flag used for the reserved-but-not-ordered business segment
- `conversion_segment`: conversion classification
- `order_id`: order identifier
- `order_time`: order timestamp

## Campaign Rules

### Campaign ID is the final analytical key

Natural-language campaign descriptions must be resolved to one unique `campaign_id` before querying the Data Mart.

Actual analytical SQL should use `campaign_id` whenever possible.

Do not use a vague pattern such as `campaign_name LIKE '%August%'` as the final analytical filter.

### Ambiguous Campaign Handling

A country, product, and month may match more than one campaign.

If multiple campaigns match, the agent must present the matching campaigns and ask the user to choose one.

The agent must not guess.

### No Campaign Match

If no campaign matches the supplied business context, tell the user that no campaign was found.

Do not silently broaden the search.

## Analysis Date vs Campaign Period

The date when an operations user asks a question is not necessarily the campaign period.

For post-campaign analysis, an analyst may ask on September 10 about a campaign that ran from August 1 to August 31.

Business data is filtered by the resolved campaign period and campaign ID, not by the date when the user asks the question.

## AI Routing Rules

### Knowledge Path

Use LlamaIndex for:

- business definitions
- metric definitions
- Data Mart metadata
- campaign rules

Examples:

- What does reserved-but-not-ordered mean?
- How is reservation-to-order conversion rate calculated?
- What is the Data Mart grain?

### Analytics Path

Use the Analytics Tool and Athena for actual data.

Examples:

- How many users reserved but did not order?
- What was the conversion rate for CMP001?
- Did user U1001 reserve in CMP001?

## Design Principle

RAG is for knowledge.

SQL is for data.

LlamaIndex answers:

"What does this mean?"

Athena answers:

"What is the actual number?"
