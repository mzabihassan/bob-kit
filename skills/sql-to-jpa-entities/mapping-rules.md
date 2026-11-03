# Mapping rules and decisions

The engine applies these rules. Read this file to settle the DECISIONS printed by `analyze` and to explain the result; the configuration keys are in `<work>/config.json`.

## Types

| SQL (PostgreSQL / Oracle) | Java | Mapping details |
| --- | --- | --- |
| `varchar(n)`, `text` / `VARCHAR2(n)` | `String` | `length = n`; PostgreSQL `text` keeps `columnDefinition = "text"`, never `@Lob` (that would map to `oid`) |
| `char(n)` / `CHAR(n)` | `String` | `@JdbcTypeCode(SqlTypes.CHAR)`; values are blank-padded by the database |
| `char(1)` with `CHECK IN ('Y','N')` or `('T','F')` | `Boolean` | `YesNoConverter` / `TrueFalseConverter` |
| `smallint`, `NUMBER(p<=4)` with `CHECK IN (0,1)` | `Boolean` | `NumericBooleanConverter` (keeps the numeric column on Oracle 23ai and PostgreSQL) |
| `boolean` / `BOOLEAN` (23ai) | `Boolean` | |
| `smallint` / `NUMBER(p<=9)` | `Short` (PostgreSQL) / `Integer` | |
| `integer` / `NUMBER(p<=9)` | `Integer` | |
| `bigint` / `NUMBER(10..19)` | `Long` | |
| `numeric(p,s)` / `NUMBER(p,s)`, s > 0 | `BigDecimal` | `precision`, `scale`; DTO `@Digits` |
| `NUMBER` without precision | `BigDecimal` (`Long` for a key) | DECISION: set `types["table.column"]` to `Long` or `Integer` when it only holds integers |
| `real`, `double precision` / `BINARY_FLOAT`, `BINARY_DOUBLE`, `FLOAT` | `Float`, `Double` | reported when the column looks monetary |
| `date` (PostgreSQL) | `LocalDate` | |
| `DATE` (Oracle) | `LocalDate` or `LocalDateTime` | DECISION: an Oracle DATE always stores a time. The engine picks `LocalDate` for names like `*_date`, `*_on`, `birth*`; confirm with the data or set `oracle_date["table.column"]` |
| `timestamp` / `TIMESTAMP` | `LocalDateTime` | |
| `timestamptz` / `TIMESTAMP WITH TIME ZONE` | `OffsetDateTime` | `TIMESTAMP WITH LOCAL TIME ZONE` -> `Instant` |
| `uuid` / `RAW(16)` | `UUID` | other `RAW(n)` -> `byte[]` |
| `json`, `jsonb` / `JSON` (21c+) | `String` | `@JdbcTypeCode(SqlTypes.JSON)`; a CLOB with `IS JSON` stays `@Lob String` |
| `bytea` / `BLOB` | `byte[]` | `@Lob` on Oracle only |
| `CLOB`, `NCLOB` | `String` | `@Lob` |
| PostgreSQL `CREATE TYPE ... AS ENUM` | Java enum | `@Enumerated(STRING)` + `@JdbcTypeCode(SqlTypes.NAMED_ENUM)` |
| `CHECK (col IN ('A','B'))` on text | Java enum | `@Enumerated(STRING)` when the values are valid Java constants, otherwise an enum with `code()` and an `AttributeConverter` |
| PostgreSQL arrays | `List<T>` | `@JdbcTypeCode(SqlTypes.ARRAY)` |
| other types (`inet`, `xml`, `interval year to month`...) | `String` | with the column definition; reported |

Enum names: the column name in PascalCase (`kyc_level` -> `KycLevel`), prefixed with the class for generic names (`status`, `type`, `role`... -> `AccountStatus`); rename with `enum_names`.

## Identifiers

| Schema | Mapping |
| --- | --- |
| Identity column, `serial`/`bigserial` | `GenerationType.IDENTITY` (Hibernate cannot batch these inserts) |
| `DEFAULT nextval('seq')`, `DEFAULT seq.NEXTVAL`, `OWNED BY`, an Oracle `BEFORE INSERT` trigger using `seq.NEXTVAL` | `SEQUENCE` with `allocationSize` = the sequence's INCREMENT BY |
| A sequence named after the table (`<table>_seq`, `seq_<table>`...) | `SEQUENCE`, DECISION: confirm that inserts use it |
| UUID primary key | `GenerationType.UUID` |
| Natural key, no generator | assigned by the application; Spring Data `save()` then calls `merge` (one extra select): implement `Persistable<ID>` if that matters |
| Composite key | `@EmbeddedId` class with `equals`/`hashCode`; foreign key parts mapped with `@MapsId("attribute")` |
| No primary key | not mapped; a NOT NULL unique key is used instead when there is one (reported) |

INCREMENT BY 1 is reported: with INCREMENT BY 50 and `allocationSize = 50`, Hibernate allocates ids in blocks. An Oracle trigger that overwrites the id unconditionally is reported: Hibernate would not know the stored id.

## Relationships

| Foreign key | Mapping |
| --- | --- |
| Plain foreign key | `@ManyToOne(fetch = LAZY)`, `optional = false` when NOT NULL, `@JoinColumn` with the constraint name |
| Unique foreign key | `@OneToOne(fetch = LAZY)` on the owning side only |
| Foreign key = primary key | `@OneToOne` + `@MapsId`: the child shares the parent's id; no inverse side (an inverse one-to-one cannot be lazy) |
| Composite foreign key | `@JoinColumns` with `referencedColumnName` |
| Foreign key to a unique key, not the primary key | `referencedColumnName`; the target class implements `Serializable` |
| Columns already mapped by the key or another association | read-only association (`insertable = false, updatable = false`) |
| Table holding only two foreign keys that form its key | `@ManyToMany` with `@JoinTable`, `Set`, on the side whose name starts the table name; `many_to_many_as_entity` keeps it as an entity |
| Association table with its own columns | entity with `@EmbeddedId` and two `@MapsId` associations |
| Foreign key to a table outside the scripts | plain column, reported |

Inverse collections (`@OneToMany(mappedBy)`) are generated by default only for compositions: `ON DELETE CASCADE` or a foreign key inside the child's primary key. They get `cascade = ALL`, `orphanRemoval = true` and `add`/`remove` helpers that set both sides. Association entities get a plain inverse collection on both sides. Any other relationship stays unidirectional (no unbounded collection loaded by accident). Add or remove one with `inverse["child_table.fk_columns"]`: the keys are listed in the report.

Association field names come from the foreign key column without `_id`, `_fk`, `_code` or the referenced column (`from_account_id` -> `fromAccount`); composite keys use the target class name. Rename with `field_names["table.column"]`.

## Columns with behaviour

- `version`, `row_version`, `lock_version`... (numeric or timestamp) -> `@Version`, no setter.
- `created_at`, `creation_date`... -> `@CreationTimestamp`, `updatable = false`; `updated_at`, `last_modified`... -> `@UpdateTimestamp` (`timestamps: "none"` leaves them plain, for Spring Data auditing).
- Computed columns (`GENERATED ALWAYS AS (...) STORED`, Oracle virtual columns) -> `@Generated`, `insertable = false, updatable = false`.
- Literal defaults (`DEFAULT 0`, `DEFAULT 'Y'`, `DEFAULT FALSE`, enum values) become the field's initial value: an insert from Java would otherwise send NULL and break NOT NULL. Function defaults (`SYSDATE`, `gen_random_uuid()`) are left to the database and listed.

## Entities, DTOs, mappers

- Entities: public no-argument constructor, getters, setters except for generated ids, versions and managed timestamps; collections initialised and exposed without setters; `equals` on the id (false while it is null), `hashCode` constant per class, `toString` with the id only. With `lombok: true`: `@Getter`/`@Setter` with `@Setter(AccessLevel.NONE)` where there is no setter; never `@Data`, `@EqualsAndHashCode` or `@ToString`.
- `XxxDto` (read): the id, the columns, the ids of the referenced rows (`customerId`, flattened for composite keys) and of many-to-many targets (`tagIds`); never entities or inverse collections.
- `XxxRequest` (create/update): no generated id, version, managed timestamp or computed column. `@NotNull` for NOT NULL columns without default (`@NotEmpty` for Oracle text, since Oracle stores '' as NULL), `@Size(max)`, `@Digits`, and `@Positive`, `@PositiveOrZero`, `@Min`, `@Max`, `@DecimalMin`, `@DecimalMax`, `@Size(min)` from simple CHECK constraints. Other CHECK constraints stay in the database and are listed.
- Mappers: MapStruct with `unmappedTargetPolicy = ERROR` (every property is mapped or explicitly ignored), null request values ignored, the primary key never changed by `updateEntity`; associations are left to the service, which loads them with `getReferenceById`. `manual` generates the same methods as plain static code.
- Repositories: `JpaRepository<Entity, Id>` plus `Optional<Entity> findByX` for each single-column unique constraint.

## Configuration keys

`base_package` (and optional `entity_package`, `dto_package`, `mapper_package`, `repository_package`), `lombok`, `mapper` (`mapstruct`, `manual`, `none`), `dto`, `repositories`, `schema_in_annotations`, `strip_prefixes`, `class_names` (`table` -> class), `field_names` (`table.column` or `table.fk_col1+fk_col2` -> field), `enum_names` (`table.column` -> enum), `inverse` (relation id -> true/false), `many_to_many_as_entity` (join tables), `exclude_tables`, `only_tables`, `oracle_date` (`table.column` -> `LocalDate`/`LocalDateTime`), `types` (`table.column` -> Java type), `timestamps` (`hibernate`, `none`).
