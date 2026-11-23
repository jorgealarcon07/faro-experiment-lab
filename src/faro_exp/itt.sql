WITH rec AS (
 SELECT account_id, count(*) recorded_rows, min(variant) logged_arm, min(probability) logged_probability,
 min(assigned_at) logged_time FROM faro_exp.recorded WHERE batch_hash=%(batch)s GROUP BY account_id
), outcomes AS (
 SELECT account_id,count(*) outcome_rows, bool_or(paid) paid,bool_or(complained) complained,
 min(window_end) window_end, min(available_at) available_at
 FROM faro_exp.outcome WHERE batch_hash=%(batch)s AND available_at<=%(as_of)s GROUP BY account_id
), unique_events AS (
 SELECT DISTINCT account_id,event_id,status,attempted_at,received_at FROM faro_exp.event
 WHERE batch_hash=%(batch)s AND received_at<=%(as_of)s
), attempts AS (
 SELECT account_id,count(*) attempts,count(*) FILTER (WHERE status='delivered') delivered,
 min(attempted_at) first_attempt,max(attempted_at) last_attempt,
 bool_or(received_at<attempted_at) event_clock FROM unique_events GROUP BY account_id
)
SELECT a.account_id,a.variant,a.assigned_at,a.probability,e.high_risk,
 coalesce(r.recorded_rows,0) recorded_rows,r.logged_arm,r.logged_probability,r.logged_time,
 coalesce(o.outcome_rows,0) outcome_rows,o.paid,o.complained,o.window_end,o.available_at,
 coalesce(d.attempts,0) attempts,coalesce(d.delivered,0) delivered,d.first_attempt,d.last_attempt,
 coalesce(d.event_clock,false) event_clock
FROM faro_exp.assignment a JOIN faro_exp.account e USING(experiment_id,account_id)
LEFT JOIN rec r USING(account_id) LEFT JOIN outcomes o USING(account_id) LEFT JOIN attempts d USING(account_id)
WHERE a.experiment_id=%(experiment)s ORDER BY a.account_id
