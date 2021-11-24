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
- `NODE_DISCONNECT_TIMEOUT`: Timeout po posledním pingu followera na leadera, než leader označí uzel za odpojený

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

Follower uzel musí iniciovat registraci k leaderovi. Jakmile obdrží heartbeat packet, zaregistruje se k leaderovi pomocí HTTP GET
requestu, ve kterém mu leader vrátí jeho barvu. Tento request follower odesílá opakovaně a na základě toho aktualizuje svou barvu. Barva followera se může změnit, pokud se změní počet uzlů při běhu aplikace.

Přidělování barev probíhá následovně: Leader má díky discovery fázi přehled o počtu ostatních uzlů. Leader zjistí, kolik uzlů musí
obarvit zeleně (`ceil(<pocet_uzlu> / 3)`). Leader přijímá HTTP get requesty a postupně uzly obarvuje vždy zeleně, dokud nevyčerpá
počet zelených barev. Po vyčerpání zelených barev obarvuje uzly červeně.

## Změna počtu uzlů v průběhu běhu aplikace

### Přidání nového uzlu
Pokud se při běhu distribuovaného systému připojí nový uzel, obdrží leader hearthbeat packet a přihlásí se k aktuálnímu leaderovi. Leader následovně dle nového stavu přebarví uzly, aby odpovídali počátečnímu zadání. Přebarvení probíhá v moment, kdy follower posílá ping packet leaderovi, leader v odpovědi tohoto requestu vrací uzlu svou barvu.

### Odebrání follower uzlu
Pokud se jakýkoliv follower uzel odpojí a přestane posílat ping requesty leaderovi, leader čeká daný čas (`NODE_DISCONNECT_TIMEOUT`). Pokud se v tomto času follower uzel nepřihlásí leaderovi, leader tento uzel označí za nevalidní, odebere ho ze svého seznamu a přebarví ostatní uzly dle počátečnímu zadání.

### Odebrání leader uzlu
Pokud se leader uzel odpojí, http ping requesty od followerů selžou, popřípadě vyprší na timeoutu. Pokud nastane tento stav, follower uzel se změní do stavu init a celý proces volby leadera probíhá znovu.

## Docker healthcheck

Follower i leader uzel pracují na tick systému, při kterém periodicky spouští svou tick funkci, která obsluhuje logiku aplikace. Při každém spuštění tick funkce zapíše uzel aktuální timestamp do souboru `health.log`. Soubor `healthcheck.py` čte obsah tohoto souboru a kontroluje, kdy naposledy uzel zapsal timestamp do souboru. Pokud od zapsání timestampu uběhlo déle než 60 sekund (nebo pokud soubor neexistuje), script vrací návratovou hodnotu 1. V opačném případě vrací návratovou hodnotu 0.

## Komunikační náročnost algoritmů

### Discovery fáze
Při discovery fázi každý uzel vysílá UDP broadcast, při kterém dává ostatním uzlům o sobě vědět. Komunikační náročnosti je `O(n)`.

### Running fáze
Při running fázi je leader v pasivní roli a follower uzly periodicky odesílají leaderovi ping requesty. Komunikační náročnosti je `O(n)`.


Leader při running fázi periodicky vysílá heartbeat packety, pro případ, že se může do sítě připojit nový uzel. Komunikační náročnosti je `O(1)`.