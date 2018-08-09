The problem with the query you are using to check for locks is that you are filtering out important information needed to solve this issue. You are only looking at the pid you are concerned about but the problem is that this pid is blocked by another session that likely has a sharelock on the table you are trying to alter. ALTER requires exclusive locks and will wait until all locks on a table are released before it can proceed. You can run the query below to find which session is blocking you ALTER statement and either pg_cancel_backend or pg_terminate_backend on the blocking pid.
 
 
select l.txn_owner,l.txn_db,l.xid,l.pid,l.txn_start,l.lock_mode,l.relation,l.granted,x.pid as blocking_pid,case when l.lockable_object_type='transactionid' then null when a.nspname is null then '<relation not in current database>' else trim(a.nspname) end as schemaname,case when l.lockable_object_type='transactionid' then null when c.relname is null then '<relation not in current database>' else trim(c.relname) end as tablename,datediff(hr,l.txn_start,getdate())||' hrs '||datediff(m,l.txn_start,getdate())%60||' mins '||datediff(s,l.txn_start,getdate())%60||' secs' as txn_duration,b.query,b.starttime as query_starttime,trim(b.text) as querytxt FROM svv_transactions l
left JOIN pg_locks x on l.relation=x.relation and l.pid<>x.pid and x.granted='t' and l.granted='f'
left join pg_class c on l.relation=c.oid
left join pg_namespace a on c.relnamespace=a.oid
left join stv_inflight b on l.xid=b.xid and l.lockable_object_type='relation'
where l.pid<>pg_backend_pid() and l.relation is not null order by l.pid;
 
 
 
 
Read more about locks here, Redshift only has a subset of the locks described here:
https://www.postgresql.org/docs/8.0/static/explicit-locking.html
 
http://docs.aws.amazon.com/redshift/latest/dg/PG_TERMINATE_BACKEND.html
http://docs.aws.amazon.com/redshift/latest/dg/PG_CANCEL_BACKEND.html
