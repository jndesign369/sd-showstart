# Venue website verification

Verified November 22, 2026. These are venue/operator websites, not resale
marketplaces or copied ConcertsSD hyperlinks. Only venue_url is updated in
the saved snapshot; display names, dates, performers, artist links, and source
collection timestamps are unchanged.

| Listing venue | Official website and verification |
| --- | --- |
| 3OZ Dive Club | [3oz Dive Club, 1060 Garnet Ave, San Diego](https://3ozdiveclub.com/) |
| Cal Coast Credit Union Open Air Theatre | [Associated Students, SDSU venue site](https://as.sdsu.edu/calcoast/) |
| Dizzy's Jazz | [Dizzy's Jazz, San Diego](https://dizzysjazz.com/) |
| Harrah's Resort Southern California | [Harrah's Resort SoCal operator site](https://harrahssocal.com/) |
| Humphreys Backstage Live | [Humphreys Backstage Live, San Diego music club](https://www.humphreysbackstagelive.com/) |
| Lou Lou's | [Lou Lou's official site](https://www.loulousclub.com/); [venue-operated calendar identifies Lou Lou's Jungle Room inside the Lafayette Hotel](https://loulous.turntabletickets.com/) |
| North Island Credit Union Amphitheatre | [Live Nation venue site, Chula Vista](https://www.northislandcreditunionamp.com/) |
| Pacific Highlands Ranch | [The Village at Pacific Highlands Ranch](https://phrvillage.com/); [press clipping hosted by the center names Gaby Aparicio performing there](https://phrvillage.com/wp-content/uploads/press/LocaleMagazine_July18Stop-Suntanning-and-Start-Singing-at-These-Summer-Shows.pdf) |
| Petco Park | [Official Padres ballpark site](https://www.mlb.com/padres/ballpark) |
| Petco Park - Gallagher Square | [Official Padres Gallagher Square page](https://www.mlb.com/padres/ballpark/gallagher-square) |
| Queen Bee's | [Queen Bee's Art & Cultural Center, San Diego](https://www.queenbeessd.com/) |
| Temper Fest, Petco Park | [Official Padres ballpark site](https://www.mlb.com/padres/ballpark); [festival FAQ identifies its physical venue as Petco Park](https://temperfest.com/faqs/) |
| The Banshee | [The Banshee Bar, 3519 El Cajon Blvd, San Diego](https://thebansheebar.com/) |
| The Holding Company | [The Holding Company, Ocean Beach](https://theholdingcompanyob.com/) |
| The Kensington Club | [Kensington Club, 4079 Adams Ave, San Diego](https://www.kensingtonclub1935.com/) |
| The Tower Bar | [The Tower Bar, 4757 University Ave, San Diego](https://www.thetowerbar.com/) |
| Viejas Arena | [Associated Students, SDSU venue site](https://as.sdsu.edu/viejas_arena/) |
| Whistle Stop | [Whistle Stop Bar, 2236 Fern Street, San Diego](https://whistlestopbar.com/) |
| Humphreys Concerts By the Bay | [Humphreys Concerts by the Bay, 2241 Shelter Island Drive](https://www.humphreysconcerts.com/) |

## Matching

Humphreys already had a URL but its configured `By The Bay` capitalization
did not match the listing's `By the Bay`. The key is now corrected, and both
configured keys and incoming venue/city keys are case-folded with whitespace
normalized before lookup. Full city keys still take precedence over the `SD`
alias; unknown venues and different cities are not guessed or merged.

For the source label `Pacific Highlands Ranch`, use the concert-hosting
Village's website rather than a generic neighborhood or recreation-center
page. For the festival-prefixed Petco Park label, use the physical venue site,
not a ticket-sales or festival homepage. Gallagher Square uses its own official
subvenue page. The source's display names remain unchanged.
