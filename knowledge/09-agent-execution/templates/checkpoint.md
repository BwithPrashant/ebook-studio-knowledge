# Checkpoint <RUN-ID> (rule ENG-002 ER-4; update ONLY after a unit is verified)
task: | role: | artifact: | unit limit: 100 lines
states: PENDING, IN_PROGRESS, VERIFIED, FAILED (VERIFIED needs a result)
unit | file or marker | state | verify command | real result | tries
U01 | | PENDING | | | 0
