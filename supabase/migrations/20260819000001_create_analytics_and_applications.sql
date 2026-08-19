create table if not exists public.applications (
  id uuid default gen_random_uuid() primary key,
  name text not null,
  phone text not null,
  certificate text not null,
  birth text,
  address text,
  received_at timestamptz default now(),
  status text default '접수대기',
  route text,
  note text
);

alter table public.applications enable row level security;

drop policy if exists "Enable insert for all users" on public.applications;
create policy "Enable insert for all users" on public.applications
  for insert with check (true);

drop policy if exists "Enable select for all users" on public.applications;
create policy "Enable select for all users" on public.applications
  for select using (true);
