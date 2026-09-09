# Cards · 10 reviewed shooting plans · 7 September (database schema + views)

- Notion URL: https://app.notion.com/p/225e60a931984e3ca151b462d20d2e63
- Page path: AI Startup Workspace / Content Engine Tool / M2 Signal + Studio · 7 September · ten-card release
- Last edited (per search index): 2026-09-08T14:21:00.000Z

Note: this is a database/data-source object, not a text page. Notion's fetch tool returns schema, views and a SQLite table definition rather than row content. The 10 individual card rows (M2-I01..I05, M2-P01..P05) are fetched and dumped separately as files 10-14 and 15-19 in this folder.

---

Here is the result of "fetch" for the Database with URL https://app.notion.com/p/225e60a931984e3ca151b462d20d2e63 as of 2026-09-08T19:xx:xxZ:

<database url="{{https://app.notion.com/p/225e60a931984e3ca151b462d20d2e63}}" inline="false">
The title of this Database is: Cards · 10 reviewed shooting plans · 7 September
<ancestor-path>
<parent-page url="https://app.notion.com/p/3d20bd21ed6a813a9a4cd8f51a28af71" title="M2 Signal + Studio · 7 September · ten-card release"/>
<ancestor-2-page url="https://app.notion.com/p/3d00bd21ed6a800fb0ffda652e539ef1" title="Content Engine Tool"/>
<ancestor-3-page url="https://app.notion.com/p/8b46efbe31a44dab8f6ebd1cc54fc518" title="AI Startup Workspace"/>
</ancestor-path>
Here are the Database's Data Sources:
You can use the "fetch" tool on the URL of any Data Source to see its full schema configuration.
<data-sources>
<data-source url="{{collection://0a53ec84-08f1-4e05-b96b-f7a579b9b060}}">
The title of this Data Source is: Cards · 10 reviewed shooting plans · 7 September

Here is the database's configurable state:
Properties with `readOnly: true` are synced or system-managed. Do not try to update their values with page update tools.
<data-source-state>
{"name":"Cards · 10 reviewed shooting plans · 7 September","schema":{
  "Age at pickup":{"description":"Source age when picked; unknown for original scripts","name":"Age at pickup","type":"number"},
  "Author":{"description":"","name":"Author","type":"text"},
  "Format":{"description":"","name":"Format","options":[{"color":"blue","name":"M2 Radar"},{"color":"green","name":"M2 Builds"},{"color":"purple","name":"M2 Teardown"}],"type":"select"},
  "Lead":{"description":"Owner presenter assignment; no default","name":"Lead","options":[{"color":"orange","name":"Max"},{"color":"pink","name":"Misha"},{"color":"gray","name":"Both"},{"color":"green","name":"Макс"},{"color":"purple","name":"Миша"}],"type":"select"},
  "Name":{"description":"Stable original card identity and title","name":"Name","type":"title"},
  "Planned seconds":{"description":"","name":"Planned seconds","type":"number"},
  "Priority":{"description":"Owner-controlled priority; empty until assigned","name":"Priority","type":"number"},
  "Publication group":{"description":"","name":"Publication group","options":[{"color":"blue","name":"Introduction"},{"color":"green","name":"Regular"}],"type":"select"},
  "Reference":{"description":"Single source URL if applicable; synthesis uses Source Reels relations","name":"Reference","type":"url"},
  "Scenes":{"description":"","name":"Scenes","type":"number"},
  "Signal":{"description":"","name":"Signal","type":"text"},
  "Source Reels":{"dataSourceUrl":"collection://accf47da-7ef3-4620-bc35-2de11170560b","description":"Reviewed reference Reels with machine transcripts; multiple references do not imply a causal performance result","name":"Source Reels","type":"relation"},
  "Spoken words":{"description":"","name":"Spoken words","type":"number"},
  "Status":{"description":"Owner workflow; left empty until assigned","name":"Status","options":[{"color":"gray","name":"Proposed"},{"color":"green","name":"Taking"},{"color":"yellow","name":"Rework"},{"color":"red","name":"Not taking"},{"color":"blue","name":"Shot"},{"color":"purple","name":"Published"}],"type":"select"},
  "Synthesis":{"description":"","name":"Synthesis","type":"checkbox"},
  "Vs author norm":{"description":"Single-source view index only; no aggregate original-card performance claim","name":"Vs author norm","type":"number"},
  "Week":{"description":"Owner-controlled planning date; empty until assigned","name":"Week","type":"date"}
},"url":"collection://0a53ec84-08f1-4e05-b96b-f7a579b9b060"}
</data-source-state>

Here is the SQLite table definition for this data source.
<sqlite-table>
CREATE TABLE IF NOT EXISTS "collection://0a53ec84-08f1-4e05-b96b-f7a579b9b060" (
	url TEXT UNIQUE,
	createdTime TEXT,
	"Author" TEXT,
	"Publication group" TEXT, -- one of ["Introduction", "Regular"]
	"Scenes" FLOAT,
	"date:Week:start" TEXT,
	"date:Week:end" TEXT,
	"date:Week:is_datetime" INTEGER,
	"Synthesis" TEXT, -- "__YES__" = true, "__NO__" = false, NULL defaults to false
	"Spoken words" FLOAT,
	"Reference" TEXT,
	"Source Reels" TEXT, -- JSON array of page URLs relating to {{collection://accf47da-7ef3-4620-bc35-2de11170560b}} data source
	"Vs author norm" FLOAT,
	"Priority" FLOAT,
	"Lead" TEXT, -- one of ["Max", "Misha", "Both", "Макс", "Миша"]
	"Signal" TEXT,
	"Age at pickup" FLOAT,
	"Planned seconds" FLOAT,
	"Status" TEXT, -- one of ["Proposed", "Taking", "Rework", "Not taking", "Shot", "Published"]
	"Format" TEXT, -- one of ["M2 Radar", "M2 Builds", "M2 Teardown"]
	"Name" TEXT
)
</sqlite-table>
</data-source>
</data-sources>
Here are the Database's Views:
<views>
<view url="{{view://95564cc8-9ca0-4dc5-a84d-216b87d11916}}">
{"dataSourceUrl":"{{collection://0a53ec84-08f1-4e05-b96b-f7a579b9b060}}","displayProperties":["Name","Publication group","Format","Synthesis","Scenes","Planned seconds","Spoken words","Source Reels","Signal","Lead","Status"],"name":"All ten reviewed shooting plans","sorts":[{"direction":"ascending","property":"Name"}],"type":"table"}
</view>
<view url="{{view://3d40bd21-ed6a-81ff-9baf-000cad3cb832}}">
{"advancedFilter":{"filters":[{"operator":"enum_is","property":"Publication group","propertyType":"select","type":"property","value":{"type":"exact","value":"Introduction"}}],"operator":"and","type":"group"},"dataSourceUrl":"{{collection://0a53ec84-08f1-4e05-b96b-f7a579b9b060}}","displayProperties":["Name","Format","Synthesis","Scenes","Planned seconds","Spoken words","Source Reels","Signal","Lead","Status"],"name":"Introduction · five shooting cards","sorts":[{"direction":"ascending","property":"Name"}],"type":"table"}
</view>
<view url="{{view://3d40bd21-ed6a-81c5-926e-000c7edabc46}}">
{"advancedFilter":{"filters":[{"operator":"enum_is","property":"Publication group","propertyType":"select","type":"property","value":{"type":"exact","value":"Regular"}}],"operator":"and","type":"group"},"dataSourceUrl":"{{collection://0a53ec84-08f1-4e05-b96b-f7a579b9b060}}","displayProperties":["Name","Format","Synthesis","Scenes","Planned seconds","Spoken words","Source Reels","Signal","Lead","Status"],"name":"Regular · five shooting cards","sorts":[{"direction":"ascending","property":"Name"}],"type":"table"}
</view>
</views>
</database>
