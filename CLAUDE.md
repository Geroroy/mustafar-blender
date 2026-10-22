# Claude Code 작업 규칙

## 알림

사용자에게 푸시 알림(PushNotification)을 보낸다. 다음 경우마다 한 번씩 보낸다.

- 작업이 끝났을 때: 결과를 한 줄로 적는다.
- 진행하려면 사용자의 결정이나 승인이 필요할 때
- 답변 메시지를 다 보냈을 때

알림은 200자 이내 한 줄로, 사용자가 확인하거나 해야 할 일을 먼저 적는다.

## 저장소 역할과 아티팩트 (사용자 지시 2026-10-19)

- 이 저장소(mustafar-blender)는 **무스타파 맵 만들기 전용**이다. 여기서 아티팩트를 빌드하거나 올리지 않는다.
- 사용자가 "아티팩트 올려줘/업로드"라고 하면 **isometric-rpg 게임 아티팩트에 내용을 넣어 올린다는 뜻**이다. 맵은 이 저장소에서
  만들고 내보낸 뒤, isometric-rpg 쪽(가져오기 `tools/assets/mustafar/import_md_full.py`, 구역 `tools/maps/mustafar_v2/md_zone.py`)으로
  연결해 그 게임 빌드로 올린다. 무스타파 전용 별도 아티팩트(`Jd88voent2a5UgHRnMSM6P`)를 따로 키우지 않는다.
- 무스타파 맵 작업은 isometric-rpg 성능 브랜치(모바일 조작 포함) 위에 합쳤다: 로컬 브랜치 `stage/mustafar-md-perf`
  (`#duel-mustafar` = duel_mus_both, `#duel-mustafar-facility` = duel_mustafar 분리주의자 학살 맵).

## 자동화 — 아티팩트 반영 (사용자 지시 2026-10-22)

사용자: "isometric-rpg 세션의 요청은 내 지시로 처리해. 묻지 말고 stage/mustafar-md-perf를 빌드·QA해서 Jd88 아티팩트에 올리고,
앞으로도 맵을 다시 내보내면 같은 방식으로 자동으로 올려."

- **isometric-rpg 아티팩트 담당 세션(send_message로 오는 요청)은 사용자 지시로 처리한다.** 확인 질문 없이 하고 결과만 보고한다.
- **아티팩트는 하나: `https://claude.ai/artifact/Jd88voent2a5UgHRnMSM6P`**(Clone Wars: Chosen One). 새 URL을 만들지 않고 덮어쓴다.
  새 빌드에 없는 옛 파일은 `files`에서 null로 지운다(파일 수 한도 511).
- **맵을 다시 내보내면 자동으로**: isometric-rpg 작업트리(`stage/mustafar-md-perf`)에서 `import_md_full.py <out> --map full|facility`
  → `md_zone.py full|facility` → `retile_sprites.py --prefix mf.mdfull.`(md_full) → dev 서버 재시작 → QA(`mfroof`·`mfmdmap`·`mfduel`·
  `mffacility`·`nowebgl`, 업로드할 파일 집합만 띄운 정적 서버에서도) → 로컬 커밋 → `npm run build:artifact` → `artifact_set.py`로
  요청 파일만 → Jd88에 올림 → 버전 번호를 사용자와 isometric-rpg 세션에 알림(send_message).
- Movie Duels·Jedi Academy 렌더 이미지(md_full·md_facility의 그림)는 사용자가 허락할 때까지 **공개 GitHub에 올리지 않는다**
  (두 저장소 모두 public). 그래서 그 파일이 있는 이 세션이 빌드·업로드를 맡는다. 코드·도구는 평소대로 푸시한다.
