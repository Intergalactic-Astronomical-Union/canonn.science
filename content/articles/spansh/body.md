Some of the most heavily used navigation equipment in the galaxy isn't bolted into a ship at all. It's a system called **[Spansh](https://spansh.co.uk)**.

It knows about billions of star systems, and most of that knowledge came from ordinary pilots going about their daily lives, with transponders sending data to the Spansh database via the [Elite Dangerous Data Network (EDDN)](/codex/elite-dangerous-data-network-eddn).

Originally built to help pilots navigate using the neutron highway, it quickly became a repository of all data in the galaxy.

## What Spansh can do

| Service | What it does |
| --- | --- |
| [Neutron Router](https://spansh.co.uk/plotter) | Fast A-to-B routes that chain neutron-star supercharges |
| [Galaxy Plotter](https://spansh.co.uk/exact-plotter) | An exact route that accounts for fuel use, refuelling stops, secondary neutron stars and FSD injection boosts |
| [Road to Riches](https://spansh.co.uk/riches) | A loop of high-value worlds (Earth-likes, water worlds, terraformables) to scan for cartographic payouts |
| [Exobiology Plotter](https://spansh.co.uk/exobiology) | A route through bodies likely to host valuable biological signals, with landmarks to help find them |
| [Fleet Carrier Router](https://spansh.co.uk/fleet-carrier) | The most efficient carrier jump sequence and its tritium cost; exports to carrier auto-plotters |
| [Trade Router](https://spansh.co.uk/trade) | Profitable commodity loops from live market data |
| Search | Filtered lookups of systems, bodies, stations, factions and carriers |
| [Neutron star map](https://spansh.co.uk/neutron-map) | Every known neutron star in the galaxy |
| [Data dumps](https://spansh.co.uk/dumps) | Bulk downloads of the galaxy data for developers and researchers |

The more advanced plotters work from nightly snapshots of the archive, so a discovery can take up to a day to show up in their results.

## What we use Spansh for

The [Canonn Signals](https://signals.canonn.tech/) page uses data from Spansh to display everything known about a system. Without it we would need to build our own database of the galaxy.

We have functionality built into the [3D maps](https://map.canonn.tech) so that you can download JSON from Spansh and display it as a route or a collection of points on the map. Spansh also supplies us with a dump of all the faction data so that we can display it on the map.

We use the [Spansh dumps](https://spansh.co.uk/dumps) for sifting through body data to find locations where certain phenomena might exist, or to pull out information about specific types of bodies for in-depth studies like the [Neutron Star study](/codex/neutron-star-study). Basically, anything that requires a survey can be pulled from a Spansh dump.

## How Spansh gets its data

Spansh has no survey fleet of its own. Almost everything it knows comes over **[EDDN](/codex/elite-dangerous-data-network-eddn)**, the Elite Dangerous Data Network: a public ZeroMQ relay run by the Elite Dangerous Community Developers ([EDCD](https://edcd.github.io/)).

When you jump, scan a body or dock, your ship writes the event to its journal. An uploader such as [EDMC](https://github.com/EDCD/EDMarketConnector) or [EDDiscovery](https://github.com/EDDiscovery/EDDiscovery) reads the journal and sends each event to EDDN. EDDN passes every message on to everyone listening: Spansh, [EDSM](https://www.edsm.net), [Inara](https://inara.cz) and many smaller projects. No single archive owns the data. They all draw from the same feed.

So Spansh is only as complete as the pilots who feed it. If no uploader has reported a system, the plotters can't see it. If your carrier or a system you know is missing from a search, check that your uploader is running and sending to EDDN.

As a Canonn member you rely on this data, so we hope you will send your data to the network too.

## Keeping the lights on

Spansh is free to use, but hosting an archive of billions of systems and running heavy route calculations costs real credits every month. Commander Spansh pays for it through pilot support on Patreon.

**Support Spansh:** [patreon.com/spansh](https://www.patreon.com/spansh)
