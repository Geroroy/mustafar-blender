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
- 대기 중인 일: isometric-rpg의 **모바일 조작 적용이 끝나면** 무스타파 맵 작업(로컬 브랜치 `stage/mustafar-blank-mdland`:
  `#duel-mustafar` = duel_mus_both, `#duel-mustafar-facility` = duel_mustafar 분리주의자 학살 맵)을 isometric-rpg 아티팩트에 합친다.
