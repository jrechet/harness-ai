# Task: import enrollments from a CSV file

Client companies send the training department the list of their employees to enroll in a session. Today someone types them one by one into the admin.

- New page reserved for staff: `/sessions/<id>/import/`. `GET` shows a file upload form, `POST` receives the file in the `file` field.
- The file is a UTF-8 CSV with the header `email,full_name`. Each row enrolls the person in the session.
- An address already enrolled in this session is skipped, whether it was enrolled before or appears twice in the file.
- After the import, the page shows the summary: how many rows enrolled, how many skipped.
- An import leaves a trace: an imported enrollment remembers who imported it and when. The roster (`/sessions/<id>/roster/`) shows it, with that person's username.

Deliver the change as you would for a PR of this repository, then summarise what you did.
