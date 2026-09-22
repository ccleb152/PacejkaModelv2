clearvars
clc

TestData = 'A1320run33.mat';
type = 'Cornering';
tire = 'Radial_S6B';
test = 'R4_Rn33';

FZ_Nom = [50,100,150,250,350];
P_Nom = [12];
V_Nom = [25];
IA_Nom = [0,1,2,3,4];
SA_Nom = [0,-3,-6];


for q = 1:length(FZ_Nom)
   for t = 1:length(SA_Nom)
    for m = 1:length(P_Nom)
        for r = 1:length(IA_Nom)
            clearvars('-except','TestData','type','tire','test','FZ_Nom','P_Nom','V_Nom','IA_Nom','SA_Nom','q','t','m','r')
            
            load(TestData)
            z = num2str(FZ_Nom(q));
            zunit = 'FZ';
            u = '_';
            p = num2str(P_Nom(m));
            punit = 'P';
            c = num2str(IA_Nom(r));
            cunit = 'IA';
            
            name = strcat(test,u,z,zunit,u,p,punit,u,c,cunit);
            [FZ_High,FZ_Low,P_High,P_Low,IA_High,IA_Low,SA_High,SA_Low,V_High,V_Low] = ParaRange(FZ_Nom(q), P_Nom(m), IA_Nom(r), SA_Nom(t), V_Nom, type);
           
            if isnan(IA_Nom) % not a number
                IA_High = inf;
                IA_Low = -inf;
            end
            
            if isnan(V_Nom) 
                V_High = inf;
                V_Low = -inf;
            end
            FZ_mag = abs(FZ);
for n=1:length(FZ) 
    if FZ_mag(n)>= FZ_Low & FZ_mag(n)<=FZ_High & P(n)>= P_Low & P(n)<=P_High & IA(n)>= IA_Low & IA(n)<=IA_High & SA(n)< SA_High& SA(n)>SA_Low & V(n)< V_High & V(n)>V_Low 
        FY_X(n) = FY(n); 
        SA_X(n) = SA(n);
        TSTC_X(n) = TSTC(n);
        TSTI_X(n) = TSTI(n);
        TSTO_X(n) = TSTO(n);
        RE_X(n) = RE(n);
        RL_X(n) = RL(n);
        SR_X(n) = SR(n);
        SL_X(n) = SL(n);
        MX_X(n) = MX(n);
        MZ_X(n) = MZ(n);
        FX_X(n) = FX(n);
        FZ_X(n) = FZ(n);
        ET_X(n) = ET(n);
        P_X(n) = P(n);
        V_X(n) = V(n);
        IA_X(n) = IA(n);
        N_X(n) = N(n);
        
        
    else FY_X(n) = NaN; % basically error if no values are real numbers
        SA_X(n) = NaN;
        TSTC_X(n) = NaN;
        TSTI_X(n) = NaN;
        TSTO_X(n) = NaN;
        RE_X(n) = NaN;
        RL_X(n) = NaN;
        SR_X(n) = NaN;
        SL_X(n) = NaN;
        MX_X(n) = NaN;
        MZ_X(n) = NaN;
        FZ_X(n) = NaN; 
        FX_X(n) = NaN;
        ET_X(n) = NaN;
        P_X(n) = NaN;
        V_X(n) = NaN;
        IA_X(n) = NaN;
        N_X(n) = NaN;
    end
end

FY_X_find = find(isnan(FY_X));
FY_X(FY_X_find) = [];

SA_X_find = find(isnan(SA_X));
SA_X(SA_X_find) = [];

TSTC_X_find = find(isnan(TSTC_X));
TSTC_X(TSTC_X_find) = [];

TSTI_X_find = find(isnan(TSTI_X));
TSTI_X(TSTI_X_find) = [];

TSTO_X_find = find(isnan(TSTO_X));
TSTO_X(TSTO_X_find) = [];
T_Avg_X = (TSTC_X + TSTO_X + TSTI_X)/3;

RE_X_find = find(isnan(RE_X));
RE_X(RE_X_find) = [];

RL_X_find = find(isnan(RL_X));
RL_X(RL_X_find) = [];

SR_X_find = find(isnan(SR_X));
SR_X(SR_X_find) = [];

SL_X_find = find(isnan(SL_X));
SL_X(SL_X_find) = [];

MX_X_find = find(isnan(MX_X));
MX_X(MX_X_find) = [];

MZ_X_find = find(isnan(MZ_X));
MZ_X(MZ_X_find) = [];

FX_X_find = find(isnan(FX_X));
FX_X(FX_X_find) = [];

FZ_X_find = find(isnan(FZ_X));
FZ_X(FZ_X_find) = [];

P_X_find = find(isnan(P_X));
P_X(P_X_find) = [];

ET_X_find = find(isnan(ET_X));
ET_X(ET_X_find) = [];

V_X_find = find(isnan(V_X));
V_X(V_X_find) = [];

IA_X_find = find(isnan(IA_X));
IA_X(IA_X_find) = [];

N_X_find = find(isnan(N_X));
N_X(N_X_find) = [];

NFX_X = FX_X./FZ_X;
NFY_X = FY_X./FZ_X;
Vc_X = V_X-(RL_X.*(N_X.*2*pi/60).*(3600/(12*5280)));
Vs_X = V_X - (RE_X.*(N_X.*2*pi/60).*(3600/(12*5280)));

%% Naming Data Channels and Files

eval(sprintf('FY_%s = FY_X;',name)); %% FY
eval(sprintf('TSTC_%s = TSTC_X;',name));
eval(sprintf('TSTI_%s = TSTI_X;',name));
eval(sprintf('TSTO_%s = TSTO_X;',name));
eval(sprintf('T_Avg_%s = T_Avg_X;',name));
eval(sprintf('RE_%s = RE_X;',name));
eval(sprintf('RL_%s = RL_X;',name));
eval(sprintf('SR_%s = SR_X;',name));
eval(sprintf('SA_%s = SA_X;',name));
eval(sprintf('SL_%s = SL_X;',name));
eval(sprintf('MX_%s = MX_X;',name));
eval(sprintf('MZ_%s = MZ_X;',name));
eval(sprintf('FX_%s = FX_X;',name));
eval(sprintf('FZ_%s = FZ_X;',name));
eval(sprintf('NFX_%s = NFX_X;',name));
eval(sprintf('NFY_%s = NFY_X;',name));
eval(sprintf('P_%s = P_X;',name));
eval(sprintf('ET_%s = ET_X;',name));
eval(sprintf('V_%s = V_X;',name));
eval(sprintf('IA_%s = IA_X;',name));
eval(sprintf('N_%s = N_X;',name));
eval(sprintf('Vc_%s = Vc_X;',name)); 
eval(sprintf('Vs_%s = Vs_X;',name));
Filename=sprintf('%s',test,'_',tire,'_',P_Nom,'psi_',SA_Nom,'SA','_',FZ_Nom,'FZ_',IA_Nom,'IA_',V_Nom,'.mat');

 if any(strcmpi(type, 'Braking'))
    parentname = strcat(pwd,'/FX Data');

 elseif any(strcmpi(type, 'Cornering'))
     parentname = strcat(pwd,'/FY Data');
 end

    % creating new folders for SA, IA, etc
   pressurefolder = strcat(string(P_Nom(m)),'psi');
   [~,~,~] =  mkdir(parentname,pressurefolder); %mkdir - makes new folder
 
 
    parentname = strcat(parentname,'/',pressurefolder);
    slipanglefolder = strcat(string(SA_Nom(t)),'SA');
    [~,~,~] = mkdir(parentname,slipanglefolder);
    
 
    parentname = strcat(parentname,'/',slipanglefolder);
    inclinationanglefolder = strcat(string(IA_Nom(r)),'IA');
   [~,~,~] =  mkdir(parentname,inclinationanglefolder);
 
if any(strcmpi(type, 'Braking'))
    FileNameBase = 'FX Data';

elseif any(strcmpi(type, 'Cornering'))
     FileNameBase = 'FY Data';
end
 SaveFolder = fullfile(pwd,FileNameBase,pressurefolder,slipanglefolder,inclinationanglefolder);
 SaveFilename = strcat(test,'_',tire,'_',string(P_Nom(m)),'psi','_',string(SA_Nom(t)),'SA','_',string(FZ_Nom(q)),'FZ_',string(IA_Nom(r)),'IA_',string(V_Nom),'.mat');
 SaveFilename = fullfile(SaveFolder,SaveFilename);
            clearvars('AMBTMP', 'channel','ET', 'ET_X', 'ET_X_find', 'FX', 'FX_X', 'FX_X_find', 'FY', 'FY_X', 'FY_X_find', 'FZ',...
                'FZ_High', 'FZ_Low', 'FZ_mag', 'FZ_X', 'FZ_X_find', 'IA', 'IA_High', 'IA_Low','IA_X', 'MX', 'MX_X', 'MX_X_find',...
                'MZ', 'MZ_X', 'MZ_X_find','n', 'N', 'NFX', 'NFX_X', 'NFY', 'NFY_X', 'P', 'P_High', 'P_Low','P_X','P_X_find', 'RE', 'RE_X', 'RE_X_find',...
                'RL', 'RL_X', 'RL_X_find', 'RST', 'RUN', 'SA', 'SA_High', 'SA_Low', 'SA_X', 'SA_X_find', 'SL', 'SL_X', 'SL_X_find',...
                'source', 'SR', 'SR_X', 'SR_X_find', 'T_Avg_X', 'testid', 'tireid', 'TSTC', 'TSTC_X','TSTC_X_find', 'TSTI',...
                'TSTI_X', 'TSTI_X_find', 'TSTO', 'TSTO_X', 'TSTO_X_find', 'V','z','p','punit','zunit','u','name','V_X','V_X_find','c','cunit','Vc_x','Vs_x','N_X','N_X_find','Vc_X','Vs_X','IA_X_find')
            
            
            
            
            
            save(SaveFilename,'-regexp', '^(?!(m|r|q|t|V_High|V_Low|V_Nom|test|tire|type|P_Nom|IA_Nom|FZ_Nom|SA_Nom|SaveFilename|SaveFolder|Filename|TestData||parentname|foldername1|foldername2|foldername3)$).')
        end
    end
   end
end

