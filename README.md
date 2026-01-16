# Cloud Computing Technologies

The first-level folders in this repo, except for `sqldb` and `webserver` represent the demos of the course. Each demo shows how to deploy the reference scenario using a specific setup and technologies.

## Reference scenario

The reference scenario consists of:

- A DB with the bank account information of some users. The DB is seeded using `sqldb/seed.sql`

    | id | name  | balance |
    |----|-------|---------|
    | 1  | Mario | 100     |
    | 2  | Luigi | 200     |

- A Web server exposing an HTTP REST API (`GET /`) to query the DB and return the table in HTML format.