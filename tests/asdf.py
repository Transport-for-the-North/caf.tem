import caf.base as cb

dvec = cb.DVector.load(r'C:/Users/Spiral/Documents/Thomas Prince/Common Analytical Framework/NoTEM/Export/TP_test_attr/Core/hb_productions/hb_normits_tem_segmented_2023_dvec.h5')

translation = dvec.zoning_system.translate(cb.ZoningSystem.get_zoning("gor"))
translation