import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Home, Building, Map, Key, DollarSign, TrendingUp,
  Loader2, Plus, ShoppingCart, Users, MapPin
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

const RealEstatePage = () => {
  const { user, refreshUser } = useAuth();
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState('market');
  
  const [market, setMarket] = useState(null);
  const [myProperties, setMyProperties] = useState([]);
  const [myRentals, setMyRentals] = useState([]);
  const [rentals, setRentals] = useState([]);
  const [statistics, setStatistics] = useState(null);
  
  const [showBuyModal, setShowBuyModal] = useState(false);
  const [selectedProperty, setSelectedProperty] = useState(null);
  const [selectedZone, setSelectedZone] = useState('');

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      const [marketRes, statsRes, rentalsRes] = await Promise.all([
        axios.get(`${API}/realestate/market`),
        axios.get(`${API}/realestate/statistics`),
        axios.get(`${API}/realestate/rentals`)
      ]);
      setMarket(marketRes.data);
      setStatistics(statsRes.data);
      setRentals(rentalsRes.data.available_rentals || []);
      
      try {
        const [myPropRes, myRentRes] = await Promise.all([
          axios.get(`${API}/realestate/my-properties`),
          axios.get(`${API}/realestate/my-rentals`)
        ]);
        setMyProperties(myPropRes.data.properties || []);
        setMyRentals(myRentRes.data.rentals || []);
      } catch (e) {}
    } catch (error) {
      console.error('Failed to load real estate data:', error);
    }
    setLoading(false);
  };

  const handleBuyProperty = async (propertyType, zoneId) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/realestate/buy`, {
        property_type: propertyType,
        zone_id: zoneId
      });
      toast.success(res.data.message);
      setShowBuyModal(false);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to buy property');
    }
    setProcessing(false);
  };

  const handleSetRent = async (propertyId, amount) => {
    try {
      const res = await axios.post(`${API}/realestate/${propertyId}/set-rent`, { rent_amount: amount });
      toast.success(res.data.message);
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to set rent');
    }
  };

  const handleRentProperty = async (propertyId, months) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/realestate/${propertyId}/rent`, { duration_months: months });
      toast.success(res.data.message);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to rent property');
    }
    setProcessing(false);
  };

  const propertyIcons = {
    apartment: '🏢', house: '🏠', villa: '🏰', office: '🏛️', shop: '🏪', warehouse: '🏭', land: '🌍'
  };

  if (loading) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-neon-cyan" />
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="realestate-page">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-orbitron font-black flex items-center gap-3">
            <Home className="w-8 h-8 text-teal-400" />
            <span>Imobiliare <span className="text-neon-cyan">REALUM</span></span>
          </h1>
          <p className="text-white/60 text-sm mt-1">Cumpără proprietăți și câștigă din chirii</p>
        </motion.div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <CyberCard className="p-4 text-center">
            <div className="text-2xl font-orbitron text-teal-400">{myProperties.length}</div>
            <div className="text-xs text-white/50">Proprietățile Mele</div>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <div className="text-2xl font-orbitron text-neon-green">
              {myProperties.reduce((sum, p) => sum + (p.current_value || 0), 0).toFixed(0)}
            </div>
            <div className="text-xs text-white/50">Valoare Totală (RLM)</div>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <div className="text-2xl font-orbitron text-neon-yellow">
              {myProperties.filter(p => p.is_rented).reduce((sum, p) => sum + (p.rent_amount || 0), 0).toFixed(0)}
            </div>
            <div className="text-xs text-white/50">Venit Lunar (RLM)</div>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <div className="text-2xl font-orbitron text-neon-purple">{statistics?.total_properties || 0}</div>
            <div className="text-xs text-white/50">Total Proprietăți</div>
          </CyberCard>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'market', label: 'Piață', icon: ShoppingCart },
            { id: 'my-properties', label: 'Proprietățile Mele', icon: Key },
            { id: 'rentals', label: 'De Închiriat', icon: Users },
            { id: 'zones', label: 'Zone', icon: Map }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 font-mono text-sm whitespace-nowrap flex items-center gap-2 transition-all ${
                activeTab === tab.id 
                  ? 'bg-teal-500/20 border border-teal-400 text-teal-400' 
                  : 'border border-white/20 text-white/60 hover:border-white/40'
              }`}
            >
              <tab.icon className="w-4 h-4" /> {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'market' && (
          <div>
            {/* Zone Filter */}
            <div className="mb-4">
              <select
                value={selectedZone}
                onChange={e => setSelectedZone(e.target.value)}
                className="bg-black/50 border border-white/20 p-2 text-white"
              >
                <option value="">Toate Zonele</option>
                {market?.zones?.map(zone => (
                  <option key={zone.id} value={zone.id}>{zone.name} ({zone.city})</option>
                ))}
              </select>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {market?.available_new
                ?.filter(p => !selectedZone || p.zone_id === selectedZone)
                .map((prop, i) => (
                <CyberCard key={i} className="p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{propertyIcons[prop.property_type]}</span>
                      <div>
                        <div className="font-orbitron text-teal-400">{prop.type_name}</div>
                        <div className="text-xs text-white/50 flex items-center gap-1">
                          <MapPin className="w-3 h-3" /> {prop.zone_name}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-mono text-neon-green text-lg">{prop.price}</div>
                      <div className="text-xs text-white/40">RLM</div>
                    </div>
                  </div>
                  
                  <div className="text-sm text-white/50 mb-3">
                    Randament chirie: <span className="text-neon-yellow">{(prop.rent_rate * 100).toFixed(0)}%</span>/lună
                  </div>
                  
                  <div className="text-xs text-white/40 mb-3">
                    Disponibile: {prop.available}
                  </div>
                  
                  <CyberButton 
                    variant="primary" 
                    size="sm" 
                    className="w-full"
                    onClick={() => handleBuyProperty(prop.property_type, prop.zone_id)}
                    disabled={processing || (user?.realum_balance || 0) < prop.price}
                  >
                    <ShoppingCart className="w-4 h-4 mr-1" /> Cumpără
                  </CyberButton>
                </CyberCard>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'my-properties' && (
          <div className="space-y-4">
            {myProperties.length > 0 ? (
              myProperties.map(prop => (
                <CyberCard key={prop.id} className="p-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <span className="text-3xl">{propertyIcons[prop.property_type]}</span>
                      <div>
                        <div className="font-orbitron text-teal-400">{prop.name}</div>
                        <div className="text-sm text-white/50">{prop.zone_name}</div>
                        <div className="text-xs text-white/40">{prop.type_name}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-mono text-neon-green text-xl">{prop.current_value?.toFixed(0)} RLM</div>
                      <div className={`text-sm ${prop.is_rented ? 'text-neon-yellow' : 'text-white/40'}`}>
                        {prop.is_rented ? `Închiriat: ${prop.rent_amount}/lună` : 'Neînchiriat'}
                      </div>
                    </div>
                  </div>
                  
                  {!prop.is_rented && (
                    <div className="mt-4 flex gap-2">
                      <input
                        type="number"
                        placeholder="Chirie/lună"
                        className="bg-black/50 border border-white/20 p-2 text-white w-32"
                        id={`rent-${prop.id}`}
                      />
                      <CyberButton 
                        variant="outline" 
                        size="sm"
                        onClick={() => {
                          const input = document.getElementById(`rent-${prop.id}`);
                          if (input.value) handleSetRent(prop.id, parseFloat(input.value));
                        }}
                      >
                        Setează Chirie
                      </CyberButton>
                    </div>
                  )}
                  
                  {prop.is_rented && (
                    <div className="mt-3 text-sm text-white/50">
                      Chiriaș: <span className="text-neon-cyan">{prop.current_tenant_username}</span>
                    </div>
                  )}
                </CyberCard>
              ))
            ) : (
              <CyberCard className="p-8 text-center">
                <Home className="w-16 h-16 mx-auto mb-4 text-teal-400/50" />
                <p className="text-white/50">Nu ai proprietăți. Cumpără una din piață!</p>
              </CyberCard>
            )}
          </div>
        )}

        {activeTab === 'rentals' && (
          <div className="space-y-4">
            {/* My Current Rentals */}
            {myRentals.length > 0 && (
              <CyberCard className="p-4 mb-6">
                <h3 className="font-orbitron text-lg mb-3">Proprietăți Închiriate de Mine</h3>
                {myRentals.map(rental => (
                  <div key={rental.id} className="p-3 bg-black/30 border border-white/10 mb-2">
                    <div className="flex justify-between">
                      <span className="text-teal-400">{rental.property_name}</span>
                      <span className="font-mono">{rental.monthly_rent} RLM/lună</span>
                    </div>
                    <div className="text-xs text-white/40 mt-1">
                      Până la: {new Date(rental.end_date).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </CyberCard>
            )}

            {/* Available Rentals */}
            <h3 className="font-orbitron text-lg mb-3">Disponibile pentru Închiriere</h3>
            {rentals.length > 0 ? (
              <div className="grid md:grid-cols-2 gap-4">
                {rentals.map(prop => (
                  <CyberCard key={prop.id} className="p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-2xl">{propertyIcons[prop.property_type]}</span>
                      <div>
                        <div className="font-orbitron text-teal-400">{prop.name}</div>
                        <div className="text-xs text-white/50">{prop.zone_name}</div>
                      </div>
                    </div>
                    <div className="text-lg font-mono text-neon-yellow mb-3">
                      {prop.rent_amount} RLM/lună
                    </div>
                    <div className="text-xs text-white/40 mb-3">
                      Proprietar: {prop.owner_username}
                    </div>
                    <div className="flex gap-2">
                      {[1, 3, 6, 12].map(months => (
                        <CyberButton 
                          key={months}
                          variant="outline" 
                          size="sm"
                          onClick={() => handleRentProperty(prop.id, months)}
                          disabled={processing}
                        >
                          {months} luni
                        </CyberButton>
                      ))}
                    </div>
                  </CyberCard>
                ))}
              </div>
            ) : (
              <CyberCard className="p-8 text-center">
                <p className="text-white/50">Nicio proprietate disponibilă pentru închiriere.</p>
              </CyberCard>
            )}
          </div>
        )}

        {activeTab === 'zones' && (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {statistics?.zone_statistics?.map(zone => (
              <CyberCard key={zone.zone.id} className="p-4">
                <div className="text-center mb-3">
                  <div className="font-orbitron text-xl text-teal-400">{zone.zone.name}</div>
                  <div className="text-sm text-white/50">{zone.zone.city}</div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-white/50">Proprietăți:</span>
                    <span className="font-mono">{zone.property_count}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-white/50">Valoare totală:</span>
                    <span className="font-mono text-neon-green">{zone.total_value?.toFixed(0)} RLM</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-white/50">Multiplicator preț:</span>
                    <span className="font-mono text-neon-yellow">{zone.zone.price_multiplier}x</span>
                  </div>
                </div>
              </CyberCard>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default RealEstatePage;
