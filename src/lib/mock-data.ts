export const countries = [
  { code: "IN", name: "India" },
  { code: "US", name: "United States" },
  { code: "GB", name: "United Kingdom" },
  { code: "CA", name: "Canada" },
  { code: "AU", name: "Australia" },
  { code: "DE", name: "Germany" },
  { code: "FR", name: "France" },
  { code: "IT", name: "Italy" },
  { code: "ES", name: "Spain" },
  { code: "JP", name: "Japan" },
  { code: "KR", name: "South Korea" },
  { code: "SG", name: "Singapore" },
  { code: "AE", name: "United Arab Emirates" },
  { code: "BR", name: "Brazil" },
  { code: "MX", name: "Mexico" },
  { code: "NL", name: "Netherlands" },
  { code: "CH", name: "Switzerland" },
  { code: "SE", name: "Sweden" },
  { code: "NZ", name: "New Zealand" },
  { code: "TH", name: "Thailand" },
];

export type BudgetLevel = "backpacker" | "budget" | "comfortable" | "premium" | "luxury";
export type TripDuration = "weekend" | "3-5-days" | "1-week" | "1-2-weeks" | "2-4-weeks" | "1-month-plus";
export type Season = "spring" | "summer" | "monsoon" | "autumn" | "winter";
export type TravelPace = "slow-relaxed" | "balanced" | "packed-schedule" | "adventure-packed";
export type Activity =
  | "hiking"
  | "beaches"
  | "trekking"
  | "scuba-diving"
  | "skiing"
  | "museums"
  | "historical-places"
  | "nightlife"
  | "shopping"
  | "food-tours"
  | "photography"
  | "wildlife"
  | "camping"
  | "road-trips"
  | "water-sports"
  | "festivals";
export type DestinationType =
  | "beaches"
  | "mountains"
  | "cities"
  | "countryside"
  | "islands"
  | "forests"
  | "deserts"
  | "historical-cities"
  | "tropical"
  | "snow";
export type Priority =
  | "price"
  | "weather"
  | "food"
  | "safety"
  | "nature"
  | "culture"
  | "nightlife"
  | "adventure"
  | "luxury"
  | "accessibility";

export type Destination = {
  id: string;
  slug: string;
  name: string;
  country: string;
  image: string;
  description: string;
  shortDescription: string;
  activities: Activity[];
  budget: BudgetLevel;
  bestSeason: Season[];
  recommendedDuration: TripDuration[];
  travelStyles: string[];
  destinationTypes: DestinationType[];
  tags: string[];
  estimatedDailyCost: number;
  matchScore?: number;
};

export const destinations: Destination[] = [
  {
    id: "1",
    slug: "bali",
    name: "Bali",
    country: "Indonesia",
    image: "https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=1600&q=80",
    description:
      "Bali is a tropical paradise known for its forested volcanic mountains, iconic rice paddies, beaches and coral reefs.",
    shortDescription: "Tropical island with culture, beaches, and lush rice terraces.",
    activities: ["beaches", "photography", "food-tours", "wildlife", "water-sports", "museums"],
    budget: "comfortable",
    bestSeason: ["summer", "autumn"],
    recommendedDuration: ["1-week", "1-2-weeks"],
    travelStyles: ["solo", "couple", "friends"],
    destinationTypes: ["tropical", "islands", "beaches"],
    tags: ["tropical", "beaches", "culture", "food"],
    estimatedDailyCost: 80,
  },
  {
    id: "2",
    slug: "kyoto",
    name: "Kyoto",
    country: "Japan",
    image: "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=1600&q=80",
    description:
      "Kyoto is famous for its classical Buddhist temples, gardens, imperial palaces, Shinto shrines and traditional wooden houses.",
    shortDescription: "Ancient capital with temples, geisha districts, and seasonal beauty.",
    activities: ["museums", "historical-places", "photography", "food-tours", "shopping"],
    budget: "premium",
    bestSeason: ["spring", "autumn"],
    recommendedDuration: ["3-5-days", "1-week"],
    travelStyles: ["solo", "couple", "family"],
    destinationTypes: ["cities", "historical-cities"],
    tags: ["culture", "history", "food", "temples"],
    estimatedDailyCost: 140,
  },
  {
    id: "3",
    slug: "paris",
    name: "Paris",
    country: "France",
    image: "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=1600&q=80",
    description:
      "Paris is known for its cafe culture, designer boutiques, and landmarks like the Eiffel Tower and Notre-Dame cathedral.",
    shortDescription: "Romantic city of lights with art, fashion, and gastronomy.",
    activities: ["museums", "shopping", "food-tours", "photography", "nightlife"],
    budget: "premium",
    bestSeason: ["spring", "summer", "autumn"],
    recommendedDuration: ["3-5-days", "1-week"],
    travelStyles: ["couple", "friends", "family"],
    destinationTypes: ["cities", "historical-cities"],
    tags: ["romance", "art", "food", "fashion"],
    estimatedDailyCost: 160,
  },
  {
    id: "4",
    slug: "santorini",
    name: "Santorini",
    country: "Greece",
    image: "https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?auto=format&fit=crop&w=1600&q=80",
    description:
      "Santorini is one of the most romantic destinations in the world, famous for its white-washed buildings and stunning sunsets.",
    shortDescription: "Iconic island with blue-domed churches and volcanic beaches.",
    activities: ["beaches", "photography", "food-tours", "nightlife"],
    budget: "premium",
    bestSeason: ["summer", "autumn"],
    recommendedDuration: ["3-5-days", "1-week"],
    travelStyles: ["couple", "friends"],
    destinationTypes: ["islands", "beaches", "historical-cities"],
    tags: ["romance", "beaches", "sunset", "food"],
    estimatedDailyCost: 180,
  },
  {
    id: "5",
    slug: "swiss-alps",
    name: "Swiss Alps",
    country: "Switzerland",
    image: "https://images.unsplash.com/photo-1527668752968-14dc70a27c95?auto=format&fit=crop&w=1600&q=80",
    description:
      "The Swiss Alps offer breathtaking mountain scenery, world-class skiing, hiking trails, and picturesque villages.",
    shortDescription: "Majestic peaks, alpine meadows, and outdoor adventure.",
    activities: ["hiking", "skiing", "photography", "camping", "road-trips"],
    budget: "luxury",
    bestSeason: ["winter", "summer"],
    recommendedDuration: ["1-week", "1-2-weeks"],
    travelStyles: ["solo", "couple", "family", "friends"],
    destinationTypes: ["mountains", "snow"],
    tags: ["mountains", "skiing", "nature", "adventure"],
    estimatedDailyCost: 250,
  },
  {
    id: "6",
    slug: "dubai",
    name: "Dubai",
    country: "United Arab Emirates",
    image: "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=1600&q=80",
    description:
      "Dubai is a city of superlatives with futuristic skyscrapers, luxury shopping, and desert adventures.",
    shortDescription: "Ultra-modern city with luxury, desert safaris, and record-breaking attractions.",
    activities: ["shopping", "nightlife", "food-tours", "photography", "water-sports"],
    budget: "luxury",
    bestSeason: ["winter", "spring"],
    recommendedDuration: ["3-5-days", "1-week"],
    travelStyles: ["friends", "family", "business-leisure"],
    destinationTypes: ["cities", "deserts"],
    tags: ["luxury", "modern", "shopping", "desert"],
    estimatedDailyCost: 220,
  },
  {
    id: "7",
    slug: "iceland",
    name: "Iceland",
    country: "Iceland",
    image: "https://images.unsplash.com/photo-1476610182048-b716b8518aae?auto=format&fit=crop&w=1600&q=80",
    description:
      "Iceland is a land of fire and ice, featuring volcanoes, hot springs, glaciers, and the Northern Lights.",
    shortDescription: "Otherworldly landscapes, geysers, and northern lights.",
    activities: ["hiking", "photography", "camping", "wildlife", "water-sports"],
    budget: "premium",
    bestSeason: ["summer", "winter"],
    recommendedDuration: ["1-week", "1-2-weeks"],
    travelStyles: ["solo", "couple", "friends"],
    destinationTypes: ["forests", "mountains"],
    tags: ["nature", "adventure", "aurora", "geothermal"],
    estimatedDailyCost: 190,
  },
  {
    id: "8",
    slug: "new-zealand",
    name: "New Zealand",
    country: "New Zealand",
    image: "https://images.unsplash.com/photo-1508193638397-1c4234db14d8?auto=format&fit=crop&w=1600&q=80",
    description:
      "New Zealand is an adventurer's playground with dramatic landscapes, Maori culture, and endless outdoor activities.",
    shortDescription: "Dramatic landscapes, Maori culture, and epic road trips.",
    activities: ["hiking", "road-trips", "camping", "photography", "water-sports", "wildlife"],
    budget: "comfortable",
    bestSeason: ["summer", "autumn"],
    recommendedDuration: ["1-2-weeks", "2-4-weeks"],
    travelStyles: ["solo", "couple", "friends", "family"],
    destinationTypes: ["mountains", "forests", "countryside"],
    tags: ["adventure", "nature", "road-trip", "culture"],
    estimatedDailyCost: 110,
  },
  {
    id: "9",
    slug: "thailand",
    name: "Thailand",
    country: "Thailand",
    image: "https://images.unsplash.com/photo-1552465011-b4e21bf6e79a?auto=format&fit=crop&w=1600&q=80",
    description:
      "Thailand offers tropical beaches, ornate temples, vibrant street food, and bustling night markets.",
    shortDescription: "Ornate temples, tropical beaches, and incredible street food.",
    activities: ["beaches", "food-tours", "museums", "nightlife", "shopping", "photography"],
    budget: "budget",
    bestSeason: ["winter", "spring"],
    recommendedDuration: ["1-week", "1-2-weeks"],
    travelStyles: ["solo", "friends", "couple", "family"],
    destinationTypes: ["tropical", "beaches", "historical-cities"],
    tags: ["budget", "food", "beaches", "temples"],
    estimatedDailyCost: 50,
  },
  {
    id: "10",
    slug: "maldives",
    name: "Maldives",
    country: "Maldives",
    image: "https://images.unsplash.com/photo-1514282401047-d79a71a590e8?auto=format&fit=crop&w=1600&q=80",
    description:
      "The Maldives is synonymous with luxury, featuring overwater bungalows, crystal-clear lagoons, and pristine coral reefs.",
    shortDescription: "Luxury overwater bungalows and turquoise lagoons.",
    activities: ["beaches", "scuba-diving", "water-sports", "photography"],
    budget: "luxury",
    bestSeason: ["winter", "spring"],
    recommendedDuration: ["3-5-days", "1-week"],
    travelStyles: ["couple", "honeymoon"],
    destinationTypes: ["islands", "tropical", "beaches"],
    tags: ["luxury", "beaches", "diving", "romance"],
    estimatedDailyCost: 350,
  },
  {
    id: "11",
    slug: "barcelona",
    name: "Barcelona",
    country: "Spain",
    image: "https://images.unsplash.com/photo-1583422409516-2895a77efded?auto=format&fit=crop&w=1600&q=80",
    description:
      "Barcelona is known for its art, architecture, Mediterranean beaches, and vibrant food scene.",
    shortDescription: "Gaudi architecture, tapas bars, and Mediterranean vibes.",
    activities: ["museums", "historical-places", "food-tours", "beaches", "nightlife", "shopping"],
    budget: "comfortable",
    bestSeason: ["spring", "summer", "autumn"],
    recommendedDuration: ["3-5-days", "1-week"],
    travelStyles: ["friends", "couple", "family"],
    destinationTypes: ["cities", "beaches", "historical-cities"],
    tags: ["architecture", "food", "beaches", "culture"],
    estimatedDailyCost: 130,
  },
  {
    id: "12",
    slug: "cappadocia",
    name: "Cappadocia",
    country: "Turkey",
    image: "https://images.unsplash.com/photo-1641128324972-af3212f0f6bd?auto=format&fit=crop&w=1600&q=80",
    description:
      "Cappadocia is famous for its fairy chimneys, cave dwellings, and unforgettable hot air balloon rides at sunrise.",
    shortDescription: "Fairy chimneys, cave hotels, and sunrise balloon rides.",
    activities: ["photography", "historical-places", "hiking", "food-tours"],
    budget: "budget",
    bestSeason: ["spring", "summer", "autumn"],
    recommendedDuration: ["3-5-days"],
    travelStyles: ["solo", "couple", "friends"],
    destinationTypes: ["historical-cities", "countryside"],
    tags: ["history", "photography", "adventure", "unique"],
    estimatedDailyCost: 60,
  },
  {
    id: "13",
    slug: "kerala",
    name: "Kerala",
    country: "India",
    image: "https://images.unsplash.com/photo-1602216056096-3b40cc0c9944?auto=format&fit=crop&w=1600&q=80",
    description:
      "Kerala is known as God's Own Country, offering serene backwaters, lush hill stations, and Ayurvedic wellness.",
    shortDescription: "Backwaters, hill stations, and Ayurvedic wellness retreats.",
    activities: ["beaches", "wildlife", "food-tours", "photography", "museums"],
    budget: "budget",
    bestSeason: ["winter", "spring", "autumn"],
    recommendedDuration: ["1-week", "1-2-weeks"],
    travelStyles: ["family", "couple", "solo"],
    destinationTypes: ["countryside", "tropical", "beaches"],
    tags: ["wellness", "nature", "food", "budget"],
    estimatedDailyCost: 45,
  },
  {
    id: "14",
    slug: "rajasthan",
    name: "Rajasthan",
    country: "India",
    image: "https://images.unsplash.com/photo-1477587458883-47145ed94245?auto=format&fit=crop&w=1600&q=80",
    description:
      "Rajasthan is the land of kings, featuring majestic forts, palaces, desert safaris, and vibrant folk culture.",
    shortDescription: "Royal forts, desert camps, and colorful folk culture.",
    activities: ["historical-places", "photography", "food-tours", "shopping", "festivals"],
    budget: "budget",
    bestSeason: ["winter"],
    recommendedDuration: ["1-week", "1-2-weeks"],
    travelStyles: ["family", "friends", "couple"],
    destinationTypes: ["deserts", "historical-cities"],
    tags: ["history", "culture", "desert", "royal"],
    estimatedDailyCost: 55,
  },
  {
    id: "15",
    slug: "tokyo",
    name: "Tokyo",
    country: "Japan",
    image: "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=1600&q=80",
    description:
      "Tokyo is a dazzling mix of ultramodern and traditional, offering high-tech attractions, ancient temples, and world-class cuisine.",
    shortDescription: "Neon-lit streets, ancient temples, and world-class food.",
    activities: ["museums", "shopping", "food-tours", "nightlife", "photography", "historical-places"],
    budget: "premium",
    bestSeason: ["spring", "autumn"],
    recommendedDuration: ["3-5-days", "1-week"],
    travelStyles: ["solo", "friends", "couple", "business-leisure"],
    destinationTypes: ["cities"],
    tags: ["urban", "food", "technology", "culture"],
    estimatedDailyCost: 170,
  },
  {
    id: "16",
    slug: "amalfi-coast",
    name: "Amalfi Coast",
    country: "Italy",
    image: "https://images.unsplash.com/photo-1534308983496-4fabb1a015ee?auto=format&fit=crop&w=1600&q=80",
    description:
      "The Amalfi Coast is a stunning stretch of coastline with colorful villages, cliffside roads, and Mediterranean charm.",
    shortDescription: "Cliffside villages, lemon groves, and coastal drives.",
    activities: ["beaches", "food-tours", "photography", "road-trips"],
    budget: "premium",
    bestSeason: ["summer", "autumn"],
    recommendedDuration: ["3-5-days", "1-week"],
    travelStyles: ["couple", "friends", "family"],
    destinationTypes: ["beaches", "countryside"],
    tags: ["coastal", "romance", "food", "scenic"],
    estimatedDailyCost: 200,
  },
  {
    id: "17",
    slug: "reykjavik",
    name: "Reykjavik",
    country: "Iceland",
    image: "https://images.unsplash.com/photo-1523528283115-3bfb3f66b2be?auto=format&fit=crop&w=1600&q=80",
    description:
      "Reykjavik is the gateway to Iceland's natural wonders, offering Northern Lights, geothermal lagoons, and volcanic landscapes.",
    shortDescription: "Gateway to Northern Lights and geothermal wonders.",
    activities: ["photography", "hiking", "nightlife", "food-tours", "wildlife"],
    budget: "premium",
    bestSeason: ["winter", "summer"],
    recommendedDuration: ["3-5-days", "1-week"],
    travelStyles: ["solo", "couple", "friends"],
    destinationTypes: ["mountains", "forests"],
    tags: ["aurora", "geothermal", "nature", "unique"],
    estimatedDailyCost: 195,
  },
  {
    id: "18",
    slug: "machu-picchu",
    name: "Machu Picchu",
    country: "Peru",
    image: "https://images.unsplash.com/photo-1526392060635-9d6019884377?auto=format&fit=crop&w=1600&q=80",
    description:
      "Machu Picchu is an ancient Incan citadel set high in the Andes Mountains, offering breathtaking views and historical significance.",
    shortDescription: "Ancient Incan citadel in the clouds.",
    activities: ["hiking", "historical-places", "photography", "trekking"],
    budget: "budget",
    bestSeason: ["autumn", "winter", "spring"],
    recommendedDuration: ["3-5-days", "1-week"],
    travelStyles: ["solo", "friends", "couple"],
    destinationTypes: ["mountains", "historical-cities"],
    tags: ["history", "trekking", "adventure", "unesco"],
    estimatedDailyCost: 70,
  },
];
