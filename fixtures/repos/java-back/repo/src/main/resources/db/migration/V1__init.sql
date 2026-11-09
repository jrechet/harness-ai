create table invoice (id bigserial primary key, customer_id varchar(64) not null, total numeric(12,2) not null);
