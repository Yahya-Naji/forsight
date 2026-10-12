-- ============================================================
-- 031 EW TREE — Electronic Warfare as the root of a traversable tree
--
--   EW
--   ├── EA  EP  ES  EMSO  CUAS   the manuals' divisions, with their
--   │                             ew_functions as leaves
--   └── CYBER  AI  PROCUREMENT    lenses on EW; their topics hang directly
--                                 under them
--
-- A strict tree, stored as a parent pointer. Every live topic has exactly one
-- home node (topics.node_id), so rolling evidence up a branch never counts a
-- topic twice. A topic's ew_functions are its cross-links: function nodes use
-- the ew_functions id as their own id, so node_topics() follows them without a
-- mapping table.
--
-- The CEMA division has no branch of its own: its three functions are placed
-- under the branch that owns them here (RF cyber → CYBER, cognitive → AI,
-- software-defined → EA).
--
-- The pillar enum is untouched. The pipeline and console still filter on it;
-- moving them onto the tree is a later step.
-- ============================================================

create table if not exists nodes (
  id            text primary key,      -- 'EW', 'EA', 'CYBER', or an ew_functions id
  parent_id     text references nodes(id),
  level         smallint not null default 0,   -- set by trigger: parent.level + 1
  kind          text not null check (kind in ('root','branch','function')),
  name          text not null,
  ew_function_id text unique references ew_functions(id),
  sort          smallint not null default 0,
  check ((kind = 'root') = (parent_id is null)),
  check ((kind = 'function') = (ew_function_id is not null))
);

-- Level is derived, never authored, and a node may not become its own ancestor.
create or replace function nodes_set_level() returns trigger
language plpgsql as $$
begin
  if new.parent_id is null then
    new.level := 0;
    return new;
  end if;
  if exists (
    with recursive up as (
      select id, parent_id from nodes where id = new.parent_id
      union all
      select n.id, n.parent_id from nodes n join up on n.id = up.parent_id
    ) select 1 from up where id = new.id
  ) then
    raise exception 'node %: parent % would create a cycle', new.id, new.parent_id;
  end if;
  select level + 1 into new.level from nodes where id = new.parent_id;
  return new;
end $$;

drop trigger if exists nodes_level on nodes;
create trigger nodes_level before insert or update of parent_id on nodes
  for each row execute function nodes_set_level();

-- ---------- the tree ----------
-- Inserted parent-first so the trigger can read each parent's level.
insert into nodes (id, parent_id, kind, name, sort) values
('EW', null, 'root', 'Electronic Warfare', 0)
on conflict (id) do update set name = excluded.name;

insert into nodes (id, parent_id, kind, name, sort) values
('EA',          'EW', 'branch', 'Electronic Attack',             1),
('EP',          'EW', 'branch', 'Electronic Protection',         2),
('ES',          'EW', 'branch', 'Electronic Support',            3),
('EMSO',        'EW', 'branch', 'Spectrum Operations',           4),
('CUAS',        'EW', 'branch', 'Counter-UAS',                   5),
('CYBER',       'EW', 'branch', 'Cybersecurity',                 6),
('AI',          'EW', 'branch', 'Artificial Intelligence',       7),
('PROCUREMENT', 'EW', 'branch', 'Procurement',                   8)
on conflict (id) do update set parent_id = excluded.parent_id,
  name = excluded.name, sort = excluded.sort;

insert into nodes (id, parent_id, kind, name, ew_function_id, sort)
select f.id,
       case f.id
         when 'CEMA-RFCYBER' then 'CYBER'
         when 'CEMA-COG'     then 'AI'
         when 'CEMA-SDR'     then 'EA'
         else f.division
       end,
       'function', f.name, f.id, 0
  from ew_functions f
on conflict (id) do update set parent_id = excluded.parent_id, name = excluded.name;

-- ---------- topic homes ----------
alter table topics add column if not exists node_id text references nodes(id);

update topics t set node_id = m.node_id
  from (values
    ('EW-T10','EA'), ('EW-T11','EA'), ('EW-T12','EP'), ('EW-T13','ES'),
    ('EW-T14','EA'), ('EW-T15','EMSO'), ('EW-T16','CUAS'), ('EW-T17','CUAS'),
    ('EW-T18','EA'), ('EW-T19','CUAS')
  ) as m(topic_id, node_id)
 where t.id = m.topic_id;

update topics set node_id = case pillar
    when 'CYBERSECURITY' then 'CYBER'
    when 'AI'            then 'AI'
    when 'PROCUREMENT'   then 'PROCUREMENT'
  end
 where pillar <> 'ELECTRONIC_WARFARE' and retired_at is null and node_id is null;

-- ---------- traversal ----------
create or replace function node_subtree(root text)
returns table (id text, parent_id text, kind text, name text, level smallint, depth int)
language sql stable as $$
  with recursive down as (
    select n.id, n.parent_id, n.kind, n.name, n.level, 0 as depth
      from nodes n where n.id = root
    union all
    select n.id, n.parent_id, n.kind, n.name, n.level, down.depth + 1
      from nodes n join down on n.parent_id = down.id
  )
  select * from down;
$$;

-- Live topics reachable from a node: homed in its subtree, or cross-linked to
-- a function in it. A topic that is both is reported once, as 'home'.
create or replace function node_topics(root text)
returns table (topic_id text, via text)
language sql stable as $$
  with sub as (select id, kind from node_subtree(root)),
  home as (
    select t.id from topics t
     where t.retired_at is null and t.node_id in (select id from sub)
  ),
  link as (
    select t.id from topics t
     where t.retired_at is null
       and t.ew_functions && array(select id from sub where kind = 'function')
       and t.id not in (select id from home)
  )
  select id, 'home'::text from home
  union all
  select id, 'link'::text from link;
$$;

-- Per-node totals over live evidence. Counts are distinct within a node, so a
-- topic reached both ways is not double-counted. evidence_home counts homed
-- topics only, and sums cleanly up the tree.
create or replace view node_rollup with (security_invoker = true) as
select n.id, n.parent_id, n.kind, n.name, n.level,
       count(distinct nt.topic_id)                                  as topics,
       count(distinct e.id)                                         as evidence,
       count(distinct e.id) filter (where nt.via = 'home')          as evidence_home,
       count(distinct es.document_id)                               as documents,
       count(distinct se.signal_id)                                 as signals
  from nodes n
  left join lateral node_topics(n.id) nt on true
  left join evidence e on e.topic_id = nt.topic_id and e.archived_at is null
  left join evidence_sources es on es.evidence_id = e.id
  left join signal_evidence se on se.evidence_id = e.id
 group by n.id, n.parent_id, n.kind, n.name, n.level;

-- ---------- read access ----------
alter table nodes enable row level security;
drop policy if exists nodes_anon_read on nodes;
create policy nodes_anon_read on nodes for select to anon using (true);
revoke insert, update, delete on nodes from anon;
grant select on nodes to anon;
grant select on node_rollup to anon;
