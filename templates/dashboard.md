---
type: dashboard
cssclasses: []
---

# Obsidian Brain Dashboard

> [[My Patterns]] — 나의 의사결정 패턴 종합

## 최근 대화
```dataview
TABLE title, date, tags
FROM "Conversations"
WHERE type = "conversation"
SORT date DESC
LIMIT 10
```

## 프로젝트별 대화 수
```dataview
TABLE length(conversations) AS "대화 수", updated
FROM "Projects"
WHERE type = "project"
SORT updated DESC
```

## 최근 업데이트된 개념
```dataview
TABLE updated, length(conversations) AS "관련 대화"
FROM "Concepts"
WHERE type = "concept"
SORT updated DESC
LIMIT 10
```

## 이번 주 대화
```dataview
LIST title
FROM "Conversations"
WHERE type = "conversation" AND date >= date(today) - dur(7 days)
SORT date DESC
```

## 태그별 대화 수
```dataview
TABLE length(rows) AS "대화 수"
FROM "Conversations"
WHERE type = "conversation"
FLATTEN tags AS tag
GROUP BY tag
SORT length(rows) DESC
LIMIT 15
```
