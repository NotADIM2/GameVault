-- GameVault database schema (PostgreSQL / Supabase)
--
-- Run once in the Supabase SQL editor on a fresh project, then seed the catalog with:
--   python -m scripts.seed
--
-- Entities:   users, developer, game, genre
-- Relations:  have (game <-> genre), library (user owns game), plays (playtime), review
--
-- Security model: the Flask server is the only client and connects with the service_role
-- key, which bypasses Row Level Security. RLS is enabled with no policies on every table,
-- so the public anon key can read or write nothing.

-- ---------------------------------------------------------------------------
-- Catalog
-- ---------------------------------------------------------------------------

create table developer (
    developer_id  bigint generated always as identity primary key,
    name          text not null unique,
    country       text
);

create table game (
    game_id       bigint primary key,              -- explicit ids keep /game/<id> URLs stable
    title         text not null,
    developer_id  bigint references developer (developer_id) on delete set null,
    price         integer not null default 0 check (price >= 0),   -- INR, 0 = free to play
    release_date  date,
    description   text,
    image_url     text not null
);

create index game_developer_idx on game (developer_id);

create table genre (
    genre_id  bigint generated always as identity primary key,
    name      text not null unique
);

-- Many-to-many: a game has one primary genre plus any number of tags.
create table have (
    game_id     bigint not null references game (game_id) on delete cascade,
    genre_id    bigint not null references genre (genre_id) on delete cascade,
    is_primary  boolean not null default false,
    primary key (game_id, genre_id)
);

create unique index have_one_primary_per_game on have (game_id) where is_primary;
create index have_genre_idx on have (genre_id);

-- ---------------------------------------------------------------------------
-- Users and ownership
-- ---------------------------------------------------------------------------

create table users (
    id             bigint generated always as identity primary key,
    username       text not null check (char_length(username) between 3 and 30),
    email          text not null unique check (email = lower(email)),
    password_hash  text not null,
    created_at     timestamptz not null default now()
);

create table library (
    user_id        bigint not null references users (id) on delete cascade,
    game_id        bigint not null references game (game_id) on delete restrict,
    purchase_date  timestamptz not null default now(),
    price_paid     integer not null check (price_paid >= 0),  -- snapshot: prices can change later
    primary key (user_id, game_id)
);

create index library_game_idx on library (game_id);

-- Playtime only exists for games the user owns (composite FK to library).
create table plays (
    user_id      bigint not null,
    game_id      bigint not null,
    hours        numeric(7, 1) not null default 0 check (hours >= 0),
    last_played  timestamptz,
    primary key (user_id, game_id),
    foreign key (user_id, game_id) references library (user_id, game_id) on delete cascade
);

-- Only owners can review, enforced by the database rather than the app.
create table review (
    review_id   bigint generated always as identity primary key,
    user_id     bigint not null references users (id) on delete cascade,
    game_id     bigint not null references game (game_id) on delete cascade,
    rating      smallint not null check (rating between 1 and 5),
    body        text check (char_length(body) <= 2000),
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now(),
    unique (user_id, game_id),
    foreign key (user_id, game_id) references library (user_id, game_id) on delete cascade
);

create index review_game_idx on review (game_id);

-- ---------------------------------------------------------------------------
-- Views: everything the store pages read. Ratings and sales are derived from real rows,
-- never stored by hand.
-- ---------------------------------------------------------------------------

create view game_catalog with (security_invoker = true) as
select
    g.game_id,
    g.title,
    g.price,
    g.release_date,
    g.description,
    g.image_url,
    d.name    as developer,
    d.country as developer_country,
    pg.name   as primary_genre,
    array(
        select gn.name
        from have h
        join genre gn on gn.genre_id = h.genre_id
        where h.game_id = g.game_id
        order by h.is_primary desc, gn.name
    ) as genres,
    r.avg_rating,
    coalesce(r.review_count, 0) as review_count,
    coalesce(o.owner_count, 0)  as owner_count
from game g
left join developer d on d.developer_id = g.developer_id
left join have hp     on hp.game_id = g.game_id and hp.is_primary
left join genre pg    on pg.genre_id = hp.genre_id
left join (
    select game_id, round(avg(rating), 1) as avg_rating, count(*) as review_count
    from review
    group by game_id
) r on r.game_id = g.game_id
left join (
    select game_id, count(*) as owner_count
    from library
    group by game_id
) o on o.game_id = g.game_id;

create view user_library with (security_invoker = true) as
select
    l.user_id,
    l.game_id,
    l.purchase_date,
    l.price_paid,
    coalesce(p.hours, 0) as hours,
    p.last_played,
    c.title,
    c.image_url,
    c.description,
    c.primary_genre,
    c.genres,
    c.developer
from library l
join game_catalog c on c.game_id = l.game_id
left join plays p on p.user_id = l.user_id and p.game_id = l.game_id;

-- ---------------------------------------------------------------------------
-- Purchase: one transaction instead of a chain of round trips from the app.
-- Returns true if the game was added, false if the user already owned it.
-- ---------------------------------------------------------------------------

create function purchase_game(p_user_id bigint, p_game_id bigint)
returns boolean
language plpgsql
as $$
declare
    v_price integer;
begin
    select price into v_price from game where game_id = p_game_id;
    if not found then
        raise exception 'game % does not exist', p_game_id using errcode = 'no_data_found';
    end if;

    insert into library (user_id, game_id, price_paid)
    values (p_user_id, p_game_id, v_price)
    on conflict (user_id, game_id) do nothing;

    if not found then
        return false;  -- already owned
    end if;

    insert into plays (user_id, game_id) values (p_user_id, p_game_id);
    return true;
end;
$$;

-- Functions are executable by PUBLIC by default; only the server may call this one.
revoke execute on function purchase_game(bigint, bigint) from public, anon, authenticated;
grant execute on function purchase_game(bigint, bigint) to service_role;

-- ---------------------------------------------------------------------------
-- Row Level Security: deny everything to anon/authenticated (no policies).
-- ---------------------------------------------------------------------------

alter table developer enable row level security;
alter table game      enable row level security;
alter table genre     enable row level security;
alter table have      enable row level security;
alter table users     enable row level security;
alter table library   enable row level security;
alter table plays     enable row level security;
alter table review    enable row level security;
