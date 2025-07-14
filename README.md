# tq

My-implementation of `ts` (task spooler.)

## Usage

```console
sh$ tq
(lists the task queue)
sh$ tq sleep 30
42
```

```console
sh$ tq list [all/pending/finished]

sh$ tq info [task-id/all]

sh$ tq kill [-sig] [task-id/all]
sh$ tq cancel [task-id/all]

sh$ tq cat [task-id]
sh$ tq tail [task-id]

sh$ tq wait task-id

sh$ tq block [task-id/all]
sh$ tq unblock
sh$ tq next

sh$ tq urgent [task-id]
sh$ tq up [task-id]
sh$ tq down [task-id]

sh$ tq clear

sh$ tq shutdown/quit
```
