-- Migration: Create profiles and user_settings tables for Railway Postgres
-- Date: 2025-11-06

create table if not exists public.profiles (
    id uuid primary key,
    email text unique,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create unique index if not exists profiles_apple_user_id_idx
    on public.profiles ((metadata->>'apple_user_id'))
    where metadata ? 'apple_user_id';

create table if not exists public.user_settings (
    user_id uuid primary key references public.profiles(id) on delete cascade,
    language text not null default 'ja',
    timezone text not null default 'Asia/Tokyo',
    notifications_enabled boolean not null default true,
    preferences jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);





