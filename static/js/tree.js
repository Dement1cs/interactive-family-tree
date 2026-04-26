// =========================================================
// Tree rendering script
// =========================================================
(async function () {
  // Make sure GoJS is loaded before doing anything else
  // Убедиться, что GoJS загружен перед выполнением остального кода
  if (typeof go === "undefined") {
    console.error("GoJS is not loaded");
    return;
  }

  // Short alias for go.GraphObject.make
  // Короткое сокращение для go.GraphObject.make
  const $ = go.GraphObject.make;




  // =========================================================
  // Diagram initialization
  // =========================================================

  // Create the main diagram inside the diagramDiv container
  // Создать основную диаграмму внутри контейнера diagramDiv
  const diagram = $(go.Diagram, "diagramDiv", {
    "undoManager.isEnabled": true,

    // Use layered layout so generations are arranged clearly
    // Использовать layered layout, чтобы поколения располагались наглядно
    layout: $(go.LayeredDigraphLayout, {
      direction: 270,      // bottom to top / снизу вверх
      layerSpacing: 70,    // distance between generations / расстояние между поколениями
      columnSpacing: 50    // distance between nodes in one level / расстояние между узлами одного уровня
    })
  });




  // =========================================================
  // Node templates
  // =========================================================

  // Person node template
  // Шаблон узла человека
  diagram.nodeTemplate =
    $(go.Node, "Auto",
      {
        // Open the person's profile page when a node is clicked
        // Открыть страницу профиля человека при клике по узлу
        click: (e, node) => {
          const id = node.data.key;
          const url = window.PERSON_URL_TEMPLATE.replace("/0?", `/${id}?`);
          window.location.href = url;
        },
        cursor: "pointer"
      },

      // Main card background
      // Основной фон карточки
      $(go.Shape, "RoundedRectangle",
        {
          strokeWidth: 1.2,
          parameter1: 10
        },
        new go.Binding("fill", "gender", g => {
          if (g === "male") return "#dbeafe";
          if (g === "female") return "#fce7f3";
          return "#f3f4f6";
        }),
        new go.Binding("stroke", "gender", g => {
          if (g === "male") return "#93c5fd";
          if (g === "female") return "#f9a8d4";
          return "#d1d5db";
        })
      ),

      // Table layout inside the person card
      // Табличное размещение элементов внутри карточки человека
      $(go.Panel, "Table",
        {
          margin: 10,
          defaultAlignment: go.Spot.Left
        },

        // Avatar area: profile photo or initials fallback
        // Область аватарки: фото профиля или инициалы, если фото нет
        $(go.Panel, "Spot",
          {
            row: 0,
            column: 0,
            rowSpan: 3,
            margin: new go.Margin(0, 12, 0, 0),
            width: 46,
            height: 46
          },

          $(go.Shape, "RoundedRectangle",
            {
              width: 46,
              height: 46,
              parameter1: 8,
              fill: "#eef2f7",
              stroke: "#cbd5e1"
            }
          ),

          $(go.Picture,
            {
              width: 46,
              height: 46,
              imageStretch: go.GraphObject.UniformToFill
            },
            new go.Binding("source", "photoSrc"),
            new go.Binding("visible", "photoSrc", v => !!v)
          ),

          $(go.TextBlock,
            {
              font: "bold 16px sans-serif",
              stroke: "#475569"
            },
            new go.Binding("text", "initials"),
            new go.Binding("visible", "photoSrc", v => !v)
          )
        ),

        // Full name
        // Полное имя
        $(go.TextBlock,
          {
            row: 0,
            column: 1,
            font: "bold 14px sans-serif",
            stroke: "#111",
            margin: new go.Margin(0, 0, 6, 0),
            maxSize: new go.Size(190, NaN),
            overflow: go.TextBlock.OverflowEllipsis
          },
          new go.Binding("text", "fullName")
        ),

        // Maiden name if present
        // Девичья фамилия, если указана
        $(go.TextBlock,
          {
            row: 1,
            column: 1,
            font: "11px sans-serif",
            stroke: "#555",
            margin: new go.Margin(0, 0, 4, 0),
            maxSize: new go.Size(190, NaN),
            overflow: go.TextBlock.OverflowEllipsis,
            visible: false
          },
          new go.Binding("text", "maidenLine"),
          new go.Binding("visible", "maidenLine", v => !!v)
        ),

        // Life dates
        // Даты жизни
        $(go.TextBlock,
          {
            row: 2,
            column: 1,
            font: "12px sans-serif",
            stroke: "#666",
            maxSize: new go.Size(190, NaN),
            overflow: go.TextBlock.OverflowEllipsis
          },
          new go.Binding("text", "lifeLine")
        )
      )
    );

  // Union node template: small point for a couple / parent union
  // Шаблон union-узла: маленькая точка для пары / союза родителей
  diagram.nodeTemplateMap.add("Union",
    $(go.Node, "Spot",
      {
        selectable: false,
        layerName: "Background"
      },
      $(go.Shape, "Circle",
        {
          width: 10,
          height: 10,
          fill: "#a1a1aa",
          stroke: "#27272a",
          strokeWidth: 1
        }
      )
    )
  );





  // =========================================================
  // Link templates
  // =========================================================

  // Link from person to union node (spouse connection)
  // Линия от человека к union-узлу (связь супругов)
  diagram.linkTemplateMap.add("Spouse",
    $(go.Link,
      {
        routing: go.Link.Normal,
        corner: 20
      },
      $(go.Shape, {
        strokeWidth: 2,
        stroke: "#8b90a0"
      })
    )
  );

  // Link from union node to child
  // Линия от union-узла к ребёнку
  diagram.linkTemplateMap.add("ParentChild",
    $(go.Link,
      {
        routing: go.Link.Orthogonal,
        corner: 20
      },
      $(go.Shape, {
        strokeWidth: 2,
        stroke: "#8b90a0"
      })
    )
  );





  // =========================================================
  // Helper functions
  // =========================================================

  // Normalize a pair so the smaller id always comes first
  // Нормализовать пару так, чтобы меньший id всегда стоял первым
  function normalizePair(a, b) {
    if (b == null) return [a, null];
    return a < b ? [a, b] : [b, a];
  }

  // Build a unique union node key from two person ids
  // Построить уникальный ключ union-узла из двух id людей
  function unionKey(a, b) {
    const [x, y] = normalizePair(a, b);
    return y == null ? `u_${x}_none` : `u_${x}_${y}`;
  }

  // Format partial dates for compact display inside the tree node
  // Форматировать неполные даты для компактного отображения в узле дерева
  function formatShortDate(year, month, day, fallback) {
    if (year) {
      if (month) {
        const mm = String(month).padStart(2, "0");
        if (day) {
          const dd = String(day).padStart(2, "0");
          return `${dd}.${mm}.${year}`;
        }
        return `${mm}.${year}`;
      }
      return String(year);
    }

    if (month) {
      const mm = String(month).padStart(2, "0");
      if (day) {
        const dd = String(day).padStart(2, "0");
        return `${dd}.${mm}`;
      }
      return mm;
    }

    if (day) {
      return String(day);
    }

    return fallback || "";
  }





  // =========================================================
  // Data loading and model building
  // =========================================================

  try {
    // Read tree_id from the current page URL
    // Считать tree_id из URL текущей страницы
    const params = new URLSearchParams(window.location.search);
    const treeId = params.get("tree_id");

    // Build API URL for loading tree data
    // Сформировать URL API для загрузки данных дерева
    let apiUrl = "/api/tree";
    if (treeId) {
      apiUrl += `?tree_id=${treeId}`;
    }

    // Fetch tree data from the server
    // Получить данные дерева с сервера
    const res = await fetch(apiUrl);
    if (!res.ok) {
      const text = await res.text();
      console.error("GET " + apiUrl + " failed:", res.status, text);
      return;
    }

    const data = await res.json();
    const persons = data.persons || [];
    const relationships = data.relationships || [];

    // Convert server-side person records into GoJS node objects
    // Преобразовать записи людей с сервера в объекты узлов GoJS
    const personNodes = persons.map(p => {
      const fullName = (
        `${p.first_name || ""} ${p.middle_name || ""} ${p.last_name || ""}`
      ).replace(/\s+/g, " ").trim() || `Person #${p.id}`;

      const maidenLine = p.maiden_name ? `maiden: ${p.maiden_name}` : "";

      const birthDisplay = formatShortDate(
        p.birth_year, p.birth_month, p.birth_day, p.birth_date
      );

      const deathDisplay = formatShortDate(
        p.death_year, p.death_month, p.death_day, p.death_date
      );

      const lifeLine = [birthDisplay, deathDisplay].filter(Boolean).join(" - ");

      const initials = (
        `${(p.first_name || "").charAt(0)}${(p.last_name || "").charAt(0)}`
      ).toUpperCase() || "?";

      const photoSrc = p.photo_filename
        ? `/static/uploads/${p.photo_filename}`
        : "";

      return {
        key: p.id,
        category: "",
        fullName,
        maidenLine,
        lifeLine,
        initials,
        photoSrc,
        gender: (p.gender || "").toLowerCase()
      };
    });

    // parentsOf: childId -> set of parent ids
    // parentsOf: childId -> множество id родителей
    const parentsOf = new Map();

    // spousePairs: set of normalized spouse pair ids
    // spousePairs: множество нормализованных пар супругов
    const spousePairs = new Set();

    // Parse all relationship records into helper structures
    // Разобрать все связи в вспомогательные структуры
    for (const r of relationships) {
      if (r.relation_type === "parent") {
        const parentId = r.person_id;
        const childId = r.relative_id;

        if (!parentsOf.has(childId)) {
          parentsOf.set(childId, new Set());
        }
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

    // unionNodes will store synthetic union points
    // unionNodes будут хранить служебные union-узлы
    const unionNodes = [];

    // links will store final GoJS links
    // links будут хранить финальные связи GoJS
    const links = [];

    // Keep track of created union nodes to avoid duplicates
    // Следить за уже созданными union-узлами, чтобы не создавать дубликаты
    const createdUnions = new Set();

    // Create one union node and spouse links if it does not exist yet
    // Создать один union-узел и связи супругов, если он ещё не создан
    function ensureUnion(a, b) {
      const key = unionKey(a, b);

      if (!createdUnions.has(key)) {
        createdUnions.add(key);

        unionNodes.push({ key, category: "Union" });

        links.push({ from: a, to: key, category: "Spouse" });
        if (b != null) links.push({ from: b, to: key, category: "Spouse" });
      }

      return key;
    }

    // Attach children to union nodes derived from their parent set
    // Привязать детей к union-узлам, построенным на основе их родителей
    for (const [childId, parentSet] of parentsOf.entries()) {
      const parents = Array.from(parentSet).sort((a, b) => a - b);

      let uKey;
      if (parents.length >= 2) {
        // If there are two or more parents, use the first two
        // Если родителей два или больше, использовать первых двух
        uKey = ensureUnion(parents[0], parents[1]);
      } else if (parents.length === 1) {
        // If there is only one parent, create a union with "none"
        // Если родитель только один, создать союз с "none"
        uKey = ensureUnion(parents[0], null);
      } else {
        continue;
      }

      links.push({ from: uKey, to: childId, category: "ParentChild" });
    }

    // Build the final GoJS model from person nodes and union nodes
    // Собрать финальную модель GoJS из узлов людей и union-узлов
    const nodes = [...personNodes, ...unionNodes];
    diagram.model = new go.GraphLinksModel(nodes, links);

    // Fit the tree to the screen and zoom out slightly for better overview
    // Вписать дерево в экран и немного уменьшить масштаб для лучшего обзора
    diagram.zoomToFit();
    diagram.scale *= 0.9;

  } catch (err) {
    console.error("Tree rendering error:", err);
  }





  
  // =========================================================
  // PNG export
  // =========================================================

  const exportBtn = document.getElementById("exportPngBtn");

  if (exportBtn) {
    exportBtn.addEventListener("click", () => {
      try {
        // Generate image data from the current diagram
        // Сгенерировать изображение на основе текущей диаграммы
        const imageData = diagram.makeImageData({
          background: "white",
          scale: 1
        });

        // Build a safe filename based on the current tree title
        // Сформировать безопасное имя файла на основе названия текущего дерева
        const link = document.createElement("a");
        const treeTitle =
          (window.CURRENT_TREE_TITLE || "family-tree")
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-+|-+$/g, "") || "family-tree";

        link.href = imageData;
        link.download = `${treeTitle}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

      } catch (err) {
        console.error("PNG export failed:", err);
        alert("Could not export the tree as PNG.");
      }
    });
  }
})();