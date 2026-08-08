# Reservation Analytics Knowledge

## Business Process
A reservation is a pre-launch intent event. An order is the downstream purchase event used to measure conversion.

## Reservation Data Mart
The trusted Reservation Data Mart grain is **User × Campaign × Product × Site**. One row represents one user's reservation-to-order state for one campaign, one product, and one site.

## Reserved User
A reserved user has `reserve_flag = 1` in the selected campaign context.

## Ordered User
An ordered user has `order_flag = 1` in the selected campaign context.

## Reserved but Not Ordered
A reserved-but-not-ordered user has `reserve_flag = 1` and `reserved_not_ordered_flag = 1`. This segment can be used by CRM workflows to target users who expressed intent but did not convert.

## Conversion Rate
Reservation-to-order conversion rate = Ordered Users / Reserved Users. Both counts must use the same resolved campaign context.

## Campaign Resolution
Natural-language descriptions must resolve to one unique `campaign_id` before business-number SQL runs. If zero campaigns match, return not found. If multiple campaigns match, ask for clarification instead of guessing.

## Knowledge vs Data
RAG explains definitions, metric rules, and Data Mart metadata. Controlled SQL returns actual business numbers from the trusted Data Mart.
