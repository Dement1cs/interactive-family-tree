(async function () {
  // Если GoJS не подключён (нет глобальной переменной go) — дальше нет смысла
  if (typeof go === "undefined") {
    console.error("GoJS is not loaded");
    return;
  }

  // Cокращение: вместо go.GraphObject.make пишем просто $
  const $ = go.GraphObject.make;

  // Создаём диаграмму внутри <div id="diagramDiv">
  const diagram = $(go.Diagram, "diagramDiv", { // создает диаграмму в div
    "undoManager.isEnabled": true, // дает память для CTRL Z/Y
    // Алгоритм авто-раскладки: строит граф слоями сверху вниз
    layout: $(go.LayeredDigraphLayout, {
      direction: 270,  // растет снизу вверх. 0 - слева на право, 90 сверху вниз, 180 с права на лево, 270 снизу вверх
      layerSpacing: 50, // расстояние между слоями
      columnSpacing: 30 // расстояние между колонками
    })
  });

  // --- Шаблон узла "человек" (прямоугольная карточка) ---
  diagram.nodeTemplate =
    $(go.Node, "Auto", // создает нод через $
      {
        cursor: "pointer", // курсор станет рукой 
        click: (e, node) => { // обработчик клика
          const id = node.data.key; // создает константу id. / node.data обычный JS объект, который лежит в модели
          const url = window.PERSON_URL_TEMPLATE.replace(/0$/, String(id)); // заменяет первое совпадение на id. ВРЕМЕННАЯ ХУЙНЯ
          window.location.href = url;
        }
      },

      // Фон карточки (скруглённый прямоугольник)
      $(go.Shape, "RoundedRectangle", // Геометрическая фигура прямоугольник со скруглением
        { fill: "white", stroke: "#d0d0d0", strokeWidth: 1 } // заливка, цвет обводки, толщина обводки
      ),

      // Внутри карточки — таблица из 2 строк: имя + даты
      $(go.Panel, "Table", { margin: 10, defaultAlignment: go.Spot.Left }, // Контейнер, который умеет раскладывать дочерние элементы. margin внутренний отступ панели от границ Node. выравнивать к левому краю
        // Строка 0: имя
        $(go.TextBlock, 
          {
            row: 0,
            font: "bold 14px sans-serif",
            stroke: "#111", //цвет текста
            margin: new go.Margin(0, 0, 6, 0), //отделить имя от дат
            maxSize: new go.Size(200, NaN), //Ограничение размера текстового блока. по высоте нет ограничений
            overflow: go.TextBlock.OverflowEllipsis // если текс не поместился будет ...
          },
          new go.Binding("text", "fullName")
        ),

        // Строка 1: даты жизни
        $(go.TextBlock,
          {
            row: 1,
            font: "12px sans-serif",
            stroke: "#666",
            maxSize: new go.Size(200, NaN),
            overflow: go.TextBlock.OverflowEllipsis
          },
          new go.Binding("text", "lifeLine") // взять текст из node.data.lifeLine
        )
      )
    );

  // --- Шаблон узла "Union" (маленькая точка — союз/пара) ---
  diagram.nodeTemplateMap.add("Union",
    $(go.Node, "Spot", // spot - тип панели. точка
      {
        selectable: false, // Нельзя выделить точку кликом
        //movable: false, // Нельзя перетаскивать union-ноду мышкой
        layerName: "Background" // рисовать этот узел на фоновом слое
      },

      // Сама точка
      $(go.Shape, "Circle",
        { width: 8, height: 8, fill: "#999", stroke: null }
      )
    )
  );

  // --- Шаблоны линий (связей) ---

  // Связь "человек -> union" (подключение супругов к точке)
  diagram.linkTemplateMap.add("Spouse",
    $(go.Link,
      { routing: go.Link.Normal, curviness: 0 }, // обычная линия
      $(go.Shape, { strokeWidth: 1, stroke: "#888" })
    )
  );

  // Связь "union -> ребёнок" (ветка к детям)
  diagram.linkTemplateMap.add("ParentChild",
    $(go.Link,
      { routing: go.Link.Orthogonal, corner: 6 }, // линия с углами + скругление
      $(go.Shape, { strokeWidth: 1, stroke: "#999" })
    )
  );

  // --- Вспомогательные функции для ключа союза (чтобы не было дублей) ---

  // Делает пару в одном порядке: (min, max)
  function normalizePair(a, b) {
    // вернём [min,max] (b может быть null)
    if (b == null) return [a, null];
    return a < b ? [a, b] : [b, a];
  }

  // Генерирует ключ union-узла: u_1_2 или u_1_none
  function unionKey(a, b) {
    const [x, y] = normalizePair(a, b);
    return y == null ? `u_${x}_none` : `u_${x}_${y}`;
  }

  try {
    // Берём данные дерева с сервера
    const res = await fetch("/api/tree");
    if (!res.ok) {
      const text = await res.text();
      console.error("GET /api/tree failed:", res.status, text);
      return;
    }

    const data = await res.json();
    const persons = data.persons || [];
    const relationships = data.relationships || [];

    // --- Узлы людей для GoJS ---
    const personNodes = persons.map(p => {
      const fullName = (`${p.first_name || ""} ${p.last_name || ""}`).trim() || `Person #${p.id}`;
      const lifeLine = [p.birth_date || "", p.death_date || ""].filter(Boolean).join(" – ");
      return { key: p.id, category: "", fullName, lifeLine };
    });

    // Build parent map: childId -> Set(parents)
    const parentsOf = new Map();
    // Build spouse pairs: Set("min:max")
    const spousePairs = new Set();

    for (const r of relationships) {
      if (r.relation_type === "parent") { //только записи родитель-ребёнок
        const parentId = r.person_id;
        const childId = r.relative_id;
        if (!parentsOf.has(childId)) parentsOf.set(childId, new Set()); //есть ли уже запись для этого ребёнка
        parentsOf.get(childId).add(parentId);
      } else if (r.relation_type === "spouse") {
        const a = r.person_id;
        const b = r.relative_id;
        if (a != null && b != null && a !== b) {
          const [x, y] = normalizePair(a, b);
          spousePairs.add(`${x}:${y}`);
        }
      }
    }

    // Объединение узлов и связей
    const unionNodes = [];
    const links = [];

    // Вспомогательная функция: убедиться в существовании узла объединения и связать с ним супругов.
    const createdUnions = new Set();

    function ensureUnion(a, b) {
      const key = unionKey(a, b);
      if (!createdUnions.has(key)) {
        createdUnions.add(key);
        unionNodes.push({ key, category: "Union" });

        // Супружеские связи (человек -> союз)
        links.push({ from: a, to: key, category: "Spouse" });
        if (b != null) links.push({ from: b, to: key, category: "Spouse" });
      }
      return key;
    }

    // Создавайте союзы из пар супругов. (даже если детей нет — красиво)
    //for (const pair of spousePairs) {
    //  const [xStr, yStr] = pair.split(":");
    //  const x = Number(xStr);
    //  const y = Number(yStr);
    //  ensureUnion(x, y);
    //}

    // Прикрепление детей к браку на основании родителей
    // Правило:
    // - 2+ родителей: берём первых двух (по возрастанию) и делаем union (даже если нет spouse)
    // - 1 родитель: union с "none"
    for (const [childId, parentSet] of parentsOf.entries()) {
      const parents = Array.from(parentSet).sort((a, b) => a - b);

      let uKey;
      if (parents.length >= 2) {
        uKey = ensureUnion(parents[0], parents[1]);
      } else if (parents.length === 1) {
        uKey = ensureUnion(parents[0], null);
      } else {
        continue;
      }

      links.push({ from: uKey, to: childId, category: "ParentChild" });
    }

    // Final model
    const nodes = [...personNodes, ...unionNodes];
    diagram.model = new go.GraphLinksModel(nodes, links);

    diagram.zoomToFit();

  } catch (err) {
    console.error("Tree rendering error:", err);
  }
})();
