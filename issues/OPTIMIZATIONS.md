Apply ALL database performance fixes from the audit report.
Priority order: Critical first, then High, then Medium.
Python must compile clean. Report every file + line changed.
Do NOT add pagination. Do NOT change models.py relationships.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 CRITICAL FIXES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

C1. Request-scoped SystemConfig cache
File: app/main/routes.py

_resolve_pricing_inputs() fires 4 SystemConfig SELECTs per property.
_get_live_meter_criteria() fires 10 more.
At N=200 properties → ~800 identical queries per render.

Step 1 — Add to routes.py (top, near other imports):
  from flask import g

Step 2 — Add this helper function:
  def _get_config_map():
      """Load SystemConfig once per request, cached on flask.g."""
      if not hasattr(g, '_sqh_config_cache'):
          g._sqh_config_cache = {
              r.key: r.value
              for r in SystemConfig.query.all()
          }
      return g._sqh_config_cache

Step 3 — Update _resolve_pricing_inputs() signature:
  def _resolve_pricing_inputs(overrides, config_map=None):
      if config_map is None:
          config_map = _get_config_map()
      # Replace every _get_system_config_float/int(key) call with:
      # float(config_map.get(key, default))

Step 4 — Update _get_live_meter_criteria():
  def _get_live_meter_criteria():
      config_map = _get_config_map()
      # Replace every SystemConfig.query.filter_by(key=...).first()
      # with config_map.get(key, default)

Step 5 — In client_dashboard (~:874–877) and agent_dashboard
  (~:982–985), pass config_map=_get_config_map() into
  _resolve_pricing_inputs() calls.

Step 6 — In admin_dashboard (~:1315), replace SystemConfig.all()
  with _get_config_map() call. Remove the redundant single-key
  lookup at ~:1280 — use config_map.get(key) instead.

Step 7 — In auth/routes.py, consolidate the duplicate
  _get_live_meter_criteria copy (:151–191) — import and use
  the one from main/routes.py instead.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
C2. admin_dashboard — fix full-table loads + N+1 chains
File: app/main/routes.py ~1239–1435
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import func

a) all_properties (~:1263) — add eager loading:
  Property.query.options(
      selectinload(Property.subdivision)
          .selectinload(Subdivision.project),
      selectinload(Property.sale_record)
          .selectinload(PropertySale.client),
      selectinload(Property.agent)
  ).all()

b) all_trip_requests (~:1273–1275) — add:
  TrippingRequest.query.options(
      selectinload(TrippingRequest.client),
      selectinload(TrippingRequest.property_item)
          .selectinload(Property.agent),
      selectinload(TrippingRequest.sale_record)
  ).all()

c) all_results (~:1304) — add:
  QualificationResult.query.options(
      selectinload(QualificationResult.user)
  ).all()

d) Eliminate QualificationResult queried 6×:
  Remove COUNT queries at :1251–1257.
  Remove recent_assessments query at :1327.
  Derive from all_results in Python:
    total_qualified = sum(
        1 for r in all_results if r.status == 'Qualified'
    )
    total_conditional = sum(
        1 for r in all_results
        if r.status == 'Conditionally Qualified'
    )
    total_not_qualified = sum(
        1 for r in all_results if r.status == 'Not Qualified'
    )
    recent_assessments = sorted(
        all_results,
        key=lambda r: r.created_at,
        reverse=True
    )[:5]

e) Eliminate TrippingRequest queried twice:
  Remove recent_trip_requests query at :1329.
  Derive: recent_trip_requests = all_trip_requests[:20]

f) Eliminate admin COUNT queries where cohort already loaded:
  Remove counts at :1246–1248.
  Derive:
    total_clients = len(all_clients)
    total_agents  = len(all_agents)

g) Project subdivision count — replace pr.subdivisions|length
  with a precomputed dict (avoids loading entire collection):
    sub_counts = dict(
        db.session.query(
            Subdivision.project_id,
            func.count(Subdivision.id)
        ).group_by(Subdivision.project_id).all()
    )
  Pass sub_counts to template context.
  In admin.html, replace pr.subdivisions|length with:
    sub_counts.get(pr.id, 0)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
C3. client_dashboard — eliminate duplicate loads + N+1
File: app/main/routes.py ~702–952
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
a) Property loaded twice — load once with eager loading:
  all_props = Property.query.filter_by(
      status='available',
      approval_status='approved'
  ).options(
      selectinload(Property.agent)
          .selectinload(User.profile),
      selectinload(Property.subdivision)
  ).order_by(Property.created_at.desc()).all()

  Replace matched_props re-query (:755–767) with Python filter:
    matched_props = [
        p for p in all_props
        if <paste existing filter conditions here>
    ]
  Remove the separate matched_props DB query entirely.

b) PropertySale queried twice — load once:
  bought_sales = PropertySale.query.filter_by(
      client_id=current_user.id
  ).options(
      selectinload(PropertySale.property_item)
          .selectinload(Property.subdivision),
      selectinload(PropertySale.property_item)
          .selectinload(Property.agent),
      selectinload(PropertySale.trip_item)
  ).order_by(PropertySale.sold_at.desc()).all()

  Remove separate :822 query. Derive:
    sold_trip_ids = {s.trip_id for s in bought_sales
                     if s.trip_id}

c) agent_contact_map loop — data already loaded via
  selectinload above, no extra queries needed:
    agent_contact_map = {}
    for _prop in all_props:
        if _prop.agent_id and _prop.agent:
            _ag = _prop.agent
            _ap = _ag.profile
            agent_contact_map[_prop.agent_id] = {
                "name": _ag.full_name,
                "contact": _ap.contact_number if _ap else None,
                "email": _ag.email,
            }

d) Defer blob columns on UserProfile to avoid loading
  up to 16MB per profile touch:
  from sqlalchemy.orm import defer
  In the UserProfile query (if any), add:
    .options(
        defer(UserProfile.avatar_data),
        defer(UserProfile.banner_data),
        defer(UserProfile.valid_id_data),
        defer(UserProfile.income_proof_data),
        defer(UserProfile.esignature_data)
    )
  Apply same defer() to any route that loads UserProfile
  in a list context (agent_contact_map, purchase_list).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟠 HIGH FIXES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

H1. Remaining template N+1s — add selectinload to backing queries

agent_dashboard my_props (~:963–966):
  Property.query.filter_by(
      approval_status='approved',
      agent_id=current_user.id   ← ADD THIS FILTER (fixes H4 too)
  ).options(
      selectinload(Property.sale_record)
          .selectinload(PropertySale.client),
      selectinload(Property.subdivision)
  ).all()

agent_dashboard my_trips (~:970–975):
  TrippingRequest.query.join(...).options(
      selectinload(TrippingRequest.client),
      selectinload(TrippingRequest.property_item)
  ).all()

index() public landing (~:644):
  Property.query.filter_by(
      status='available',
      approval_status='approved'
  ).options(
      selectinload(Property.subdivision)
  ).all()

admin_property_purchase_list (~:3842):
  TrippingRequest.query.filter(...).options(
      selectinload(TrippingRequest.client)
          .selectinload(User.profile),
      selectinload(TrippingRequest.property_item)
          .selectinload(Property.agent),
      selectinload(TrippingRequest.sale_record)
  ).all()

admin_user_profile client branch (~:1579–1587):
  .options(selectinload(PropertySale.property_item))

admin_user_profile agent branch (~:1604–1613):
  .options(
      selectinload(PropertySale.property_item),
      selectinload(PropertySale.client)
  )

agent_property_full_detail_requests (~:3470–3471):
  .options(
      selectinload(
          PropertyPricingDetailRequestHistory.client
      )
  )

H3. Public landing — derive DISTINCTs from loaded list
File: app/main/routes.py ~594–599

Load properties first (with selectinload from H1 above),
then replace the two DISTINCT queries:
  cities    = sorted({p.citymun_name for p in properties
                      if p.citymun_name})
  locations = sorted({p.location for p in properties
                      if p.location})
Remove queries at :594 and :599 entirely.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟡 MEDIUM FIXES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

M1. Connection pool sizing
File: app/config.py ~35–47

In MySQL branch engine_options dict, add:
  "pool_size": 10,
  "max_overflow": 20,
Keep existing pool_pre_ping and pool_recycle. Do not
touch SQLite branch.

M2. Fix index-defeating predicate
File: app/main/routes.py ~1252

BEFORE:
  func.date(QualificationResult.created_at) == date.today()
AFTER:
  from datetime import datetime, date, time, timedelta
  today = date.today()
  today_start = datetime.combine(today, time.min)
  today_end   = today_start + timedelta(days=1)
  # Use in filter:
  QualificationResult.created_at >= today_start,
  QualificationResult.created_at <  today_end

M5. Fix query-in-loop in sync
File: app/main/routes.py ~56–63

Before the loop, prefetch all existing notes into a set:
  existing_notes = {
      r.notes for r in
      HistoricalBuyer.query
          .with_entities(HistoricalBuyer.notes)
          .filter(HistoricalBuyer.notes.isnot(None))
          .all()
  }
Inside loop, replace .first() check with:
  if marker in existing_notes:
      continue

M6. Derive user counts from already-loaded cohorts
File: app/main/routes.py ~1246–1248

After all_clients and all_agents are loaded:
  total_clients = len(all_clients)
  total_agents  = len(all_agents)
Remove the separate COUNT queries.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 INDEX MIGRATION FILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generate migrations/add_indexes.sql with these indexes.
Also update migrations/schema.sql CREATE TABLE blocks.

-- CRITICAL
ALTER TABLE properties
    ADD INDEX IF NOT EXISTS idx_properties_status_approval_created
        (status, approval_status, created_at);

ALTER TABLE qualification_results
    ADD INDEX IF NOT EXISTS idx_qr_user_created
        (user_id, created_at);

ALTER TABLE training_data
    ADD INDEX IF NOT EXISTS idx_td_notes (notes(64));

-- HIGH
ALTER TABLE property_sales
    ADD INDEX IF NOT EXISTS idx_ps_agent_sold (agent_id, sold_at),
    ADD INDEX IF NOT EXISTS idx_ps_client_sold (client_id, sold_at);

ALTER TABLE agent_notifications
    ADD INDEX IF NOT EXISTS idx_an_agent_type_read_created
        (agent_id, event_type, is_read, created_at);

ALTER TABLE tripping_requests
    ADD INDEX IF NOT EXISTS idx_trip_client_created
        (client_id, created_at),
    ADD INDEX IF NOT EXISTS idx_trip_property_status_read
        (property_id, status, notification_read);

-- MEDIUM
ALTER TABLE agent_availability
    DROP INDEX IF EXISTS idx_agent_availability_agent,
    DROP INDEX IF EXISTS idx_agent_availability_date,
    ADD INDEX IF NOT EXISTS idx_aa_agent_date
        (agent_id, available_date),
    ADD INDEX IF NOT EXISTS idx_aa_date (available_date);

ALTER TABLE property_pricing_detail_requests
    ADD INDEX IF NOT EXISTS idx_ppdr_status (status);

ALTER TABLE property_pricing_detail_request_history
    ADD INDEX IF NOT EXISTS idx_pdrh_request_status
        (request_id, status),
    ADD INDEX IF NOT EXISTS idx_pdrh_property_requested
        (property_id, requested_at);

ALTER TABLE users
    ADD INDEX IF NOT EXISTS idx_users_role_active_created
        (role, is_active, created_at);

-- Make implicit FK indexes explicit in schema.sql only
-- (InnoDB already created these — no ALTER needed on live DB)
-- Add to schema.sql CREATE TABLE blocks:
-- properties: idx_properties_agent_id, idx_properties_subdivision_id
-- tripping_requests: idx_trip_property_id
-- agent_notifications: idx_an_property_id
-- ppdr: idx_ppdr_reviewed_by
-- ppdrh: idx_pdrh_reviewed_by

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AFTER ALL FIXES — RUN IN ORDER:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. python -m py_compile app/main/routes.py app/auth/routes.py
   app/client/routes.py app/config.py
2. node --check static/js/*.js
3. Run migrations/add_indexes.sql against Aiven MySQL
4. Smoke test: load admin dashboard, client dashboard,
   agent dashboard, and public landing page
5. Report all files + line numbers changed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONSTRAINTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Do NOT change models.py relationship definitions
- Do NOT add pagination
- Do NOT touch frontend templates except admin.html
  sub_counts fix (C2g)
- Follow existing sqh- design system for any template edits
- All imports must follow existing import block style