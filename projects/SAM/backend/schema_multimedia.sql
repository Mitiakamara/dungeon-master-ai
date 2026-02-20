-- Add image_url to characters table to store avatar/generated images
alter table characters add column if not exists image_url text;
