# KIV/DS Distribuovaná aplikace pro volbu leadera
Aplikace je implementována v jazyce Python

## Spuštění aplikace
Aplikaci lze sestavit a spustit pomocí nástrojů Vagrant a Docker. Sestavení a spuštění lze docílit pomocí příkazu `vagrant up`.

## Konfigurace aplikace
Počet uzlů lze měnit pomocí proměnné `NODES_COUNT` definované v souboru `Vagrantfile`. Minimální počet uzlů je 3.

Další parametry aplikace lze měnit v bloku `CONFIGURABLE CONSTANTS` v souboru `node.py`. Jde o následující parametry:
- `INTERFACE_NAME`: Název interface, na kterém probíhá komunikace
- `BROADCAST_PORT`: Port, na kterém probíhá komunikace prostředníctvím UDP broadcastu
- `BROADCAST_IP`: Broadcast IP adresa na vybraném interface
- `HTTP_PORT`: Port, na kterém poslouchá http server leadera na registraci uzlů
- `NEW_CLIENT_TIMEOUT`: Timeout po posledním přidání nového uzlu, než začne výběr leadera

## Popis běhu aplikace
Každý uzel může nabývat následujících stavů:
- init
- leader
- follower

Každý uzel při spuštění začíná ve stavu init.

### Stav init
Ve stavu init probíhá discovery fáze, kdy si každý uzel vytváří seznam ostatních uzlů v síti.
Toto zjišťování probíhá pomocí UDP broadcastu na daném interface. Každý uzel zároveň vysílá i přijímá
discovery zprávy a ukládá si seznam IP adres odstatních uzlů.

Jakmile po daném timeoutu uzel nenachází nový uzel, probíha selekce leadera. Selekce leadera probíhá pomocí
Bully algoritmu. Každý uzel se podívá na nejvyšší číslo IP adresy. Pokud daný uzel má nejvyšší adresu, prohlásí
se za leadera.

Ostatní uzly, které nemají nejvyšší adresu, čekají na heartbeat UDP broadcast packet od leadera. Přijmutím tohoto packetu
se dostávají do následujícího stavu -- follower. Díky tomuto mechanismu dokáže systém přijímat nové uzlu kdykoliv za běhu
aplikace, přestože již byl vybrán leader. Nový uzel ve stavu init ihned dostane heartbeat packet a zaregistruje se k danému
leaderovi.

### Stav leader a follower
Jakmile se uzel prohlásí za leadera, začne poslouchat na nakonfigurovaném portu, kde spustí HTTP server pro registraci follower
uzlů. Jakmile je HTTP server úspěšně spuštěný, leader začne vysílat heartbeat packety a je připravený pro registraci uzlů.

Follower uzel musí iciovat registraci k leaderovi. Jakmile obdrží heartbeat packet, zaregistruje se k leaderovi pomocí HTTP GET
requestu, ve kterém mu leader vrátí jeho barvu.

Přidělování barev probíhá následovně: Leader má díky discovery fázi přehled o počtu ostatních uzlů. Leader zjistí, kolik uzlů musí
obarvit zeleně (`ceil(<pocet_uzlu> / 3)`). Leader přijímá HTTP get requesty a postupně uzly obarvuje vždy zeleně, dokud nevyčerpá
počet zelených barev. Po vyčerpání zelených barev obarvuje uzly červeně.

## Změna počtu uzlů v průběhu běhu aplikace

Aplikce dokáže reagovat na přidávání nových uzlů a dle popsaného algoritmu dokáže validně obarvit nové uzly aby splňovali zadání.
Aplikace nedokáže validně reagovat na odebírání uzlů.
